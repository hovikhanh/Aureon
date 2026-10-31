"""#1 MEETING_MINUTES "Biên bản họp" (04 §5 #1, P0; M2.3 R-DEC-99).

A meeting-minutes document carries a repeatable row-group of action items; each row feeds
`ACT-create_action_item` (title/owner/due). Owner and due are confidence-gated (04 §7) — an
ambiguous owner match goes to review before commit. `pillars=[]` = all-company.
"""

from app.modules.idp.services.catalog.base import doc_type, f

_ACTION_ITEM = "ACT-create_action_item"


MEETING_MINUTES = doc_type(
    "MEETING_MINUTES", "Biên bản họp", "Meeting minutes", [], 2,
    ["biên bản", "cuộc họp", "quyết định", "người phụ trách", "hạn", "thành phần",
     "meeting minutes", "action item", "biên bản họp"],
    [_ACTION_ITEM],
    [
        f("action_item_title", "text", _ACTION_ITEM, "title", required=True,
          aliases=("việc cần làm", "nhiệm vụ", "action item")),
        f("action_item_owner", "text", _ACTION_ITEM, "owner_name",
          aliases=("người phụ trách", "phụ trách", "owner")),
        f("action_item_due", "date", _ACTION_ITEM, "due_date",
          aliases=("hạn", "deadline", "due")),
    ],
    [],
)  # fmt: skip
