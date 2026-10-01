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

    from ssb_parquedit import ParquEdit

    REASONS = [
        "OTHER_SOURCE",
        "REVIEW",
        "OWNER",
        "MARGINAL_UNIT",
        "DUPLICATE",
        "OTHER",
    ]

    con = ParquEdit()

    get_version, set_version = mo.state(0)
    return REASONS, con, get_version, json, mo, np, pd, set_version


@app.cell
def _(mo, table_dropdown):
    mo.md("""
    # Parqueditor

    I denne appen kan du manuelt editere en Parquedit-tabell.

    Endringshistorikken vises nederst på siden.
    """)
    return


@app.cell
def _(con, mo):
    try:
        tables = con.list_tables()
    except Exception:
        mo.stop(
            mo.md(
                """
                ## Kunne ikke hente Parquedit-tabeller

                Kontroller at:
                - Du har startet tjenesten med riktig team
                - At Parqueditor er skrudd på for teamet i Dapla Ctrl
                """
            )
        )

    if not tables:
        mo.stop(
            mo.md(
                """
                ## Fant ingen Parquedit-tabeller for gjeldende team

                Kontroller at du har startet tjenesten med riktig team.
                """
            )
        )

    table_dropdown = mo.ui.dropdown(
        options=tables,
        searchable=True,
        allow_select_none=False,
        value=tables[0],
    )
    table_dropdown
    return (table_dropdown,)


@app.cell
def _(con, get_version, mo, table_dropdown):
    _ = get_version()
    df = con.view(table_name=table_dropdown.value)

    table_view = mo.ui.table(
        data=df,
        selection="single",
        pagination=True,
        page_size=10,
    )
    table_view
    return df, table_view


@app.cell
def _(REASONS, df, mo, np, pd, table_view):
    selected_rows = table_view.value

    # handle dataframe, dict and list as selection:
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

        # create input fields for all columns except for rowid
        editable_cols = [c for c in df.columns if c != "rowid"]
        widgets = {}

        for _col in editable_cols:
            val = selected_row.get(_col)

            # convert numbers to standard python types
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

        # create input fields for Parquedit metadata
        widgets["_reason"] = mo.ui.dropdown(
            options=REASONS,
            value="REVIEW",
            label="Årsak til endring (change_event_reason)",
        )
        widgets["_comment"] = mo.ui.text_area(
            placeholder="Begrunnelse for korrigeringen...",
            label="Kommentar (change_comment)",
        )

        # create form
        edit_form = mo.ui.dictionary(widgets).form(
            submit_button_label="Lagre endring med Parquedit",
            clear_on_submit=True,
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
    con,
    df,
    edit_form,
    get_version,
    mo,
    selected_row,
    set_version,
    table_dropdown,
):
    mo.stop(
        edit_form is None or edit_form.value is None or selected_row is None,
        mo.md(""),
    )

    form_data = edit_form.value
    submitted_rowid = selected_row["rowid"]
    event_reason = form_data["_reason"]
    event_comment = form_data["_comment"]

    # find changed values
    changes_dict = {}
    for _col in [c for c in df.columns if c != "rowid"]:
        new_value = form_data.get(_col)
        old_value = selected_row.get(_col)
        if str(new_value) != str(old_value):
            changes_dict[_col] = new_value

    # submit the edits to Parquedit
    if changes_dict:
        con.edit(
            table_name=table_dropdown.value,
            rowid=submitted_rowid,
            changes=changes_dict,
            change_event_reason=event_reason,
            change_comment=event_comment,
        )
        set_version(get_version() + 1)
    return


@app.cell
def _(con, get_version, json, mo, table_dropdown):
    _ = get_version()

    edits_df = con.get_edits(table_name=table_dropdown.value)

    if edits_df is None or edits_df.empty:
        log_view = mo.md("_Ingen endringer registrert i loggen ennå._")
    else:
        # get the last 10 edits
        last_edits = edits_df.tail(10).iloc[::-1]
        cards = []

        for _idx, _row in last_edits.iterrows():
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
                before = old_vals.get(k, "-")
                after = new_vals.get(k, "-")
                diff_rows.append(f"| `{k}` | `{before}` | **`{after}`** |")

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
                    f"### 📜 Siste {len(last_edits)} editeringer i Parquedit (totalt {len(edits_df)})"
                ),
                mo.md("\n".join(cards)),
            ]
        )

    log_view
    return


if __name__ == "__main__":
    app.run()
