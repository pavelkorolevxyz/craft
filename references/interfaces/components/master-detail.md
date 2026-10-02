# Master-detail

To pair a list with details, use `split-workspace.html`. The list and details use the ready theme background, with no one-off shades. The selected row gets an accent title and a 2 px marker on the edge facing the details. On mobile the marker moves to the bottom. Do not show selection with a fill or a full row border.

Track the selected record and focus separately. The record change handler updates `aria-selected`. Do not move focus into the details on every arrow key. On mobile, after an explicit open, scroll the user to the details or show them next to the record. When filtering, the selected record either stays in the set or resets to a clear empty state.
