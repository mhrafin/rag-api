---
name: 01-mvp-api
status: ongoing
---
## Functional Requirements


| ID  | Requirement                                                                                                                                                                |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| fr1 | A user must be able to upload a document file.                                                                                                                             |
| fr2 | A user must be able to get a document by id and delete a document by id.                                                                                                   |
| fr3 | Uploaded file must not exceed 50MB. Unsupported content types are rejected.                                                                                                |
| fr4 | A document is processed (pending / processing / ready / failed). Only chunks of ready documents are queryable.                                                            |
| fr5 | A user must be able to query the global knowledge base and get an LLM response with inline citations plus references.                                                     |
| fr6 | After querying, if the top n similarity of chunks are below 30% then instead of calling an llm the system should say there are not enough relevent documents to the chunk. |
| fr7 | Querying when no ready document exists, the system should inform the user of that and not call the llm with empty context.                                                 |

## Non Functional Requirements


| ID   | Requirement                                                                                                     |
| ---- | --------------------------------------------------------------------------------------------------------------- |
| nfr1 | The file processing process must survive disruptions like API restart, worker crash, embedding provider outage. |
| nfr2 | The whole api is rate limited to 10 burst, 2/sec                                                               |

## Out of Scope


| No. | Item                                           |
| --- | :--------------------------------------------- |
| 1   | Projects / collections / per-document grouping |
| 2   | Per user isolation / multi-tenancy             |
| 3   | Query result caching                           |
| 4   | Paper metadata extraction                      |

## UX

### User Scenario

A user wants to upload some documents and later ask questions over all of them.

### User Stories

User Story Template: As a [type of user], I want [an action] so that [a benefit].


| No. | User Story                                                                                                         |
| --- | ------------------------------------------------------------------------------------------------------------------ |
| 0   | As a user, I want to upload a document so that I can ask questions over it.                                        |
| 1   | As a user, I want to check a document's status so that I know when it is ready to be queried.                      |
| 2   | As a user, I want to ask a question so that I get an answer from an LLM based on my documents, with cited sources. |
| 3   | As a user, I want each cited claim to carry its marker inline so that I can trace it.                             |
