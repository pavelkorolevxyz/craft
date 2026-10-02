# Loading

Do not use generic gray boxes. The loading state belongs to the area waiting for data. A table keeps its column headers and says "Loading records", a list keeps its header, a form blocks submit and labels the action.

The area gets `aria-busy="true"`. For a long operation, use labeled [progress](progress.md).
