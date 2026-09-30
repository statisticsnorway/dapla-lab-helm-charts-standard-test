# /// script
# dependencies = [
#     "marimo>=0.25.0",
#     "numpy==2.5.3",
#     "pandas==3.0.6",
#     "polars==1.44.2",
#     "ssb-parquedit==0.1.0",
# ]
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="full", app_title="Parqeditor")


@app.cell
def _():
    import marimo as mo
    from datetime import date
    import numpy as np
    import polars as pl
    import pandas as pd
    import json
    import os

    from ssb_parquedit import ParquEdit

    TABLE_NAME = os.environ["PARQUEDIT_TABLE_NAME"]
    REASONS = [
        "OTHER_SOURCE",
        "REVIEW",
        "OWNER",
        "MARGINAL_UNIT",
        "DUPLICATE",
        "OTHER",
    ]

    con = ParquEdit()

    # Reaktiv teller for å trigge oppfrisking av data ved redigering
    get_version, set_version = mo.state(0)
    return REASONS, TABLE_NAME, con, get_version, json, mo, np, pd, set_version


@app.cell(hide_code=True)
def _(TABLE_NAME, mo):
    mo.md(f"""
    # Parqueditor

    I denne appen kan du manuelt editere en rad i en Parquedit-tabellen `{TABLE_NAME}`. Under ser du loggene for de 10 siste editeringene.
    """)
    return


@app.cell
def _(TABLE_NAME, con, get_version, mo):
    # Lytter på versjonstelleren slik at con.view kjøres på nytt når du lagrer
    _ = get_version()
    df = con.view(table_name=TABLE_NAME)

    table_view = mo.ui.table(
        data=df,
        selection="single",
        pagination=True,
        page_size=10,
        label="Velg rad for redigering",
    )
    table_view
    return df, table_view


@app.cell
def _(REASONS, df, mo, np, pd, table_view):
    selected_rows = table_view.value

    # Håndter både DataFrame, list og dict fra table_view.value
    has_selection = False
    if selected_rows is not None:
        if hasattr(selected_rows, "empty"):
            has_selection = not selected_rows.empty
        elif len(selected_rows) > 0:
            has_selection = True

    if has_selection:
        if hasattr(selected_rows, "iloc"):
            selected_row = selected_rows.iloc[0].to_dict()
        elif isinstance(selected_rows, list):
            selected_row = selected_rows[0]
        else:
            selected_row = dict(selected_rows)

        rowid_val = selected_row.get("rowid")

        # Lag inputfelter for kolonnene unntatt rowid
        editable_cols = [c for c in df.columns if c != "rowid"]
        widgets = {}

        for _col in editable_cols:
            val = selected_row.get(_col)

            # Konverter eksplisitt til standard Python int/float for å unngå TypeErrors i Marimo
            if (
                pd.notna(val)
                and isinstance(val, (int, float, np.integer, np.floating))
                and not isinstance(val, bool)
            ):
                clean_num = (
                    int(val) if isinstance(val, (int, np.integer)) else float(val)
                )
                widgets[_col] = mo.ui.number(value=clean_num, label=_col)
            else:
                widgets[_col] = mo.ui.text(
                    value=str(val) if pd.notna(val) else "", label=_col
                )

        # Parquedit metadata
        widgets["_reason"] = mo.ui.dropdown(
            options=REASONS,
            value="REVIEW",
            label="Årsak til endring (change_event_reason)",
        )
        widgets["_comment"] = mo.ui.text_area(
            placeholder="Begrunnelse for korrigeringen...",
            label="Kommentar (change_comment)",
        )

        edit_form = mo.ui.dictionary(widgets).form(
            submit_button_label="Lagre endring med Parquedit"
        )

        edit_ui = mo.vstack(
            [
                mo.md(f"### ✏️ Redigerer rad `rowid`: `{rowid_val}`"),
                edit_form,
            ]
        )
    else:
        edit_form = None
        selected_row = None
        edit_ui = mo.md("> 💡 *Velg en rad i tabellen over for å starte redigering.*")

    edit_ui
    return edit_form, selected_row


@app.cell
def _(
    TABLE_NAME,
    con,
    df,
    edit_form,
    get_version,
    mo,
    selected_row,
    set_version,
):
    mo.stop(
        edit_form is None or edit_form.value is None or selected_row is None,
        mo.md(""),
    )

    form_data = edit_form.value
    submitted_rowid = selected_row["rowid"]

    event_reason = form_data["_reason"]
    event_comment = form_data["_comment"]

    # Finn felter som faktisk er modifisert
    changes_dict = {}
    for _col in [c for c in df.columns if c != "rowid"]:
        ny_verdi = form_data.get(_col)
        gammel_verdi = selected_row.get(_col)
        if str(ny_verdi) != str(gammel_verdi):
            changes_dict[_col] = ny_verdi

    if changes_dict:
        con.edit(
            table_name=TABLE_NAME,
            rowid=submitted_rowid,
            changes=changes_dict,
            change_event_reason=event_reason,
            change_comment=event_comment,
        )
        # Trigger refresh av både tabell og logg
        set_version(get_version() + 1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Historikk over endringer
    """)
    return


@app.cell
def _(TABLE_NAME, con, get_version, json, mo):
    # Lytter på tilstandsendring slik at loggen alltid er oppdatert
    _ = get_version()

    edits_df = con.get_edits(table_name=TABLE_NAME)

    if edits_df is None or edits_df.empty:
        log_view = mo.md("_Ingen endringer registrert i loggen ennå._")
    else:
        # Hent de siste 10 endringene og vis den nyeste først
        siste_10 = edits_df.tail(10).iloc[::-1]
        cards = []

        for _idx, _row in siste_10.iterrows():
            extra_info = _row.get("commit_extra_info", {})

            if isinstance(extra_info, str):
                try:
                    extra_info = json.loads(extra_info)
                except Exception:
                    extra_info = {}
            elif not isinstance(extra_info, dict):
                extra_info = {}

            change_type = extra_info.get("change_type", "UPDATE")
            reason = extra_info.get("change_event_reason", "UKJENT")
            changed_by = extra_info.get("changed_by", "Ukjent bruker")
            rid = extra_info.get("rowid", _row.get("rowid", "-"))
            comment = extra_info.get("change_comment", "-")

            user_id_dict = extra_info.get("user_defined_id", {})
            user_id_str = (
                " | ".join([f"**{k}:** `{v}`" for k, v in user_id_dict.items()])
                if user_id_dict
                else f"**rowid:** `{rid}`"
            )

            old_vals = extra_info.get("old_values", {})
            new_vals = extra_info.get("new_values", {})
            all_keys = set(old_vals.keys()).union(set(new_vals.keys()))

            diff_rows = []
            for k in sorted(all_keys):
                før = old_vals.get(k, "-")
                etter = new_vals.get(k, "-")
                diff_rows.append(f"| `{k}` | `{før}` | **`{etter}`** |")

            diff_table = (
                "\n".join(diff_rows)
                if diff_rows
                else "| - | Ingen endringer oppgitt | - |"
            )

            cards.append(f"""
    #### 🔹 {change_type} av `{changed_by}` (rowid: `{rid}`)
    * **Enhet:** {user_id_str}
    * **Årsak:** `{reason}` | **Kommentar:** *"{comment}"*

    | Felt | Gammel verdi | Ny verdi |
    | :--- | :--- | :--- |
    {diff_table}

    ---
    """)

        log_view = mo.vstack(
            [
                mo.md(
                    f"### 📜 Siste {len(siste_10)} editeringer i Parquedit (totalt {len(edits_df)})"
                ),
                mo.md("\n".join(cards)),
            ]
        )

    log_view
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
