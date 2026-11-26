"""Patient-list adherence tags (Round 55, Section C).

Thin UI glue over src/models/adherence: configures the
adh_green / adh_amber / adh_red Treeview tags (AFTER the debt
tag, so an adherence signal wins over both the rotating name
palette and debt red) and hands the shell the {file: colour}
map for the rows it is about to insert. No signal = no tag =
the existing name colours stand.
"""
from src.models.adherence import COLOURS, adherence_for_files


def configure(tree, font):
    """Configure the three adherence tags on `tree`."""
    for name, hexcol in COLOURS.items():
        tree.tag_configure(f"adh_{name}", foreground=hexcol, font=font)


def colours_for(file_numbers):
    """{file_number: colour_or_None} for the listed patients
    (one batched query for the whole list)."""
    return {fid: c for fid, (c, _e)
            in adherence_for_files(file_numbers).items()}


def colour_for(fid):
    """Adherence colour for ONE patient (the select_patient
    insert path), or None when there is no signal."""
    return colours_for([fid]).get(fid)
