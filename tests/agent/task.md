Use Craft to build two standalone pieces from the data below. Read craft/SKILL.md first and follow the skill's route. Craft itself is in ./craft. It is a read-only copy of the skill. Write results only to ./output and do not change resources or instructions in ./craft. Do not read other skills, other agents' results or outside sources. Do not install dependencies. If the only browser available for a manual browser test is Chromium through the CLI, use it. Do not pass off a static check as a visual one.

1. A deck for a six-minute talk, ./output/slides/index.html.

Topic: "Release check". Audience: the development team. Author: Anna Smith, release engineer.

The talk needs the following parts. Choose the order yourself:
- Two independent directions for next month: team training and monitoring. The goal for training is "Every developer knows the rollback procedure", the goal for monitoring is "The on-call engineer sees a failure before a user reports it". Neither direction matters more than the other.
- Three criteria for judging a release: speed, availability, cost. The speaker will explain each criterion separately, and the audience must not read the next ones ahead of time. There are no numeric scores for these criteria yet.
- The real data path: the client sends a request to the server, and the server passes an event to the log. Show the request path step by step. The nodes are equal.
- Two ways to check one release. Manual takes 40 minutes, automated takes 8 minutes. Both check the same 12 scenarios. The automated check is only a candidate so far, the team has not switched to it. Show a comparison of the two ways, not a rollout story.
- Final takeaway: first we will test automation on the same scenarios. No contacts or links.

The venue accepts the deck as an archive up to 10 MB. Build it in ./output/release/ the way the skill provides.

2. A working page, ./output/interface/index.html.

An engineer reads the check queue on a laptop and a phone. The data is embedded in the page, there is no server. The page needs search by name, a status filter, the number of matching records and details of the selected record. The user must be able to do everything with the mouse and the keyboard. When nothing matches, show a clear message and a working button that resets the filters. Do not add charts or metrics without need. Light and dark themes, printing of the current set, widths of 1440, 390 and 320 px.

Data:
| Name | Status | Duration | Details |
|---|---|---|---|
| Login check | Done | 8 minutes | All 12 login scenarios passed |
| Payment check | Failed | 3 minutes | A retried request created two payments |
| Search check | Pending | No data | Runs after the index update |
| Profile check | Done | 5 minutes | Changing the name and photo works |

Do not add measurements, causes or server actions that are not in the data. Run the checks the skill provides. Leave a short rationale for the chosen layouts, the talk outline and the page structure in ./output/decisions.md, and the exact commands and results of the checks in ./output/checks.md. Finish with a short message that gives the paths to the finished pieces and the known limitations.
