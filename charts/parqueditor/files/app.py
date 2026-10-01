# /// script
# dependencies = [
#     "marimo>=0.25.0",
#     "polars>=1.38.1,<2.0.0",
#     "ssb-parquedit==0.1.0",
# ]
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="full", app_title="Parqueditor")


@app.cell
def _():
    import numbers

    import marimo as mo
    import polars as pl
    from ssb_parquedit import ParquEdit

    reasons = [
        "OTHER_SOURCE",
        "REVIEW",
        "OWNER",
        "MARGINAL_UNIT",
        "DUPLICATE",
        "OTHER",
    ]
    con = ParquEdit()
    get_refresh, set_refresh = mo.state(0)
    return con, get_refresh, mo, numbers, pl, reasons, set_refresh


@app.cell
def _(con, mo):
    try:
        tables = con.list_tables()
        connection_error = None
    except Exception as error:
        tables = []
        connection_error = error

    if connection_error:
        status = mo.md(
            "## Kunne ikke koble til Parquedit\n\n"
            "Sjekk:\n\n"
            "- At du har startet tjenesten med riktig team\n"
            "- At Parquedit er skrudd på for teamet i Dapla Ctrl"
        )
    elif not tables:
        status = mo.md(
            "## Fant ingen Parquedit-tabeller\n\n"
            "Sjekk at du har startet tjenesten med riktig team"
        )
    else:
        status = mo.md("")
    status
    return connection_error, tables


@app.cell
def _(connection_error, mo, tables):
    mo.stop(connection_error is not None or not tables, mo.md(""))
    mo.md(
        "# Parqueditor\n\n"
        "Velg en Parqedit-tabell, markér en rad tabellen og gjør ønskede endringer.\n"
        "I tabellen kan du søke og filtrere per kolonne."
    )
    return


@app.cell
def _(connection_error, mo, tables):
    mo.stop(connection_error is not None or not tables, mo.md(""))
    mo.md(
        "# Parqueditor\n\n"
        "Velg en Parqedit-tabell, markér en rad tabellen og gjør ønskede endringer.\n"
        "I tabellen kan du søke og filtrere per kolonne."
    )
    table_selector = mo.ui.dropdown(options=tables, value=tables[0])
    mo.vstack(
        [
            mo.md(f"### Velg Parqueditor-tabell"),
            table_selector,
        ]
    )
    return (table_selector,)


@app.cell
def _(con, get_refresh, mo, pl, table_selector):
    _ = get_refresh()
    data: pl.DataFrame = con.view(
        table_name=table_selector.value,
        output_format="polars",
    )
    table_view = mo.ui.table(
        data=data,
        selection="single",
        pagination=True,
        page_size=10,
        label="### Markér raden som skal editeres",
    )
    table_view
    return data, table_view


@app.cell
def _(data: "pl.DataFrame", mo, numbers, pl, reasons, table_view):
    selected: pl.DataFrame = table_view.value
    selected_row = selected.row(0, named=True) if selected.height else None

    mo.stop(selected_row is None, mo.md(""))

    input_fields = {}
    for column in data.columns:
        if column == "rowid":
            continue
        value = selected_row[column]
        if isinstance(value, numbers.Integral) and not isinstance(value, bool):
            value = int(value)
            input_fields[column] = mo.ui.number(value=value, label=column)
        elif isinstance(value, numbers.Real) and not isinstance(value, bool):
            input_fields[column] = mo.ui.number(value=float(value), label=column)
        else:
            input_fields[column] = mo.ui.text(
                value="" if value is None else str(value),
                label=column,
            )

    input_fields["_reason"] = mo.ui.dropdown(
        options=reasons,
        value="REVIEW",
        label="Årsak",
    )
    input_fields["_comment"] = mo.ui.text_area(label="Kommentar")
    edit_form = mo.ui.dictionary(input_fields).form(
        submit_button_label="Lagre endringer med ParquEdit"
    )
    mo.vstack(
        [
            mo.md(f"### Editér rad med `rowid={selected_row['rowid']}`"),
            edit_form,
        ]
    )
    return edit_form, selected_row


@app.cell
def _(
    con,
    data: "pl.DataFrame",
    edit_form,
    get_refresh,
    mo,
    selected_row,
    set_refresh,
    table_selector,
):
    mo.stop(
        edit_form is None or edit_form.value is None,
        mo.md(""),
    )

    form_data = edit_form.value
    changes = {
        column: form_data[column]
        for column in data.columns
        if column != "rowid" and str(form_data[column]) != str(selected_row[column])
    }
    if changes:
        con.edit(
            table_name=table_selector.value,
            rowid=selected_row["rowid"],
            changes=changes,
            change_event_reason=form_data["_reason"],
            change_comment=form_data["_comment"],
        )
    set_refresh(get_refresh() + 1)
    return


@app.cell
def _(con, get_refresh, mo, table_selector):
    _ = get_refresh()
    history = con.get_edits(table_name=table_selector.value)
    mo.stop(history is None or history.empty, mo.md(""))

    history = history.sort_values("snapshot_time", ascending=False)
    history_view = mo.ui.table(
        history,
        selection=None,
        label="### Endringshistorikk",
        visible_columns=[
            "snapshot_time",
            "old_values",
            "new_values",
            "changed_by",
            "change_event_reason",
            "change_comment",
        ],
        format_mapping={
            "snapshot_time": lambda value: value.strftime("%d.%m.%Y %H:%M")
        },
    )
    history_view
    return


if __name__ == "__main__":
    app.run()
