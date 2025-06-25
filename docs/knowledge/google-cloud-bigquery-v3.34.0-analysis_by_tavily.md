# Google Cloud BigQuery Python Client v3.34.0 API anlysis

This document analyzes the main interfaces and capabilities of the `google-cloud-bigquery` Python client library, version 3.34.0. The primary entry point for interacting with the BigQuery API is the `google.cloud.bigquery.client.Client` class.

## Core Component: `bigquery.Client`

The `Client` class is the main interface for developers to interact with Google BigQuery. It handles authentication, request formation, and response parsing.

---

## Main Interfaces and Capabilities

Here is a breakdown of the key methods available in the `bigquery.Client` class, which represent the core functionalities of the library.

### Dataset Management

| Method | Summary | Input Parameters | Output |
| :--- | :--- | :--- | :--- |
| `create_dataset` | Creates a new dataset. | `dataset` (Dataset/DatasetReference/str), `exists_ok` (bool) | `Dataset` |
| `get_dataset` | Fetches a dataset resource from the API. | `dataset_ref` (DatasetReference/str) | `Dataset` |
| `update_dataset` | Updates properties of an existing dataset. | `dataset` (Dataset), `fields` (Sequence[str]) | `Dataset` |
| `delete_dataset` | Deletes a dataset. | `dataset` (Dataset/DatasetReference/str), `delete_contents` (bool), `not_found_ok` (bool) | `None` |
| `list_datasets` | Lists datasets in a project. | `project` (str), `include_all` (bool), `filter` (str), `max_results` (int), `page_token` (str), `page_size` (int) | `Iterator[DatasetListItem]` |

### Table Management

| Method | Summary | Input Parameters | Output |
| :--- | :--- | :--- | :--- |
| `create_table` | Creates a new table. | `table` (Table/TableReference/str), `exists_ok` (bool) | `Table` |
| `get_table` | Fetches a table resource from the API. | `table` (Table/TableReference/str) | `Table` |
| `update_table` | Updates properties of an existing table. | `table` (Table), `fields` (Sequence[str]) | `Table` |
| `delete_table` | Deletes a table. | `table` (Table/TableReference/str), `not_found_ok` (bool) | `None` |
| `list_tables` | Lists tables in a dataset. | `dataset` (Dataset/DatasetReference/str), `max_results` (int), `page_token` (str), `page_size` (int) | `Iterator[TableListItem]` |

### Query Execution and Job Management

| Method | Summary | Input Parameters | Output |
| :--- | :--- | :--- | :--- |
| `query` | Submits a SQL query for execution. | `query` (str), `job_config` (QueryJobConfig) | `QueryJob` |
| `query_and_wait` | Submits a query, waits for completion, and returns results. | `query` (str), `job_config` (QueryJobConfig), `wait_timeout` (float) | `RowIterator` |
| `get_job` | Fetches a job resource. | `job_id` (str), `location` (str), `project` (str) | `QueryJob`, `LoadJob`, etc. |
| `cancel_job` | Cancels a running job. | `job_id` (str), `location` (str), `project` (str) | `Job` |
| `list_jobs` | Lists jobs in a project. | `project` (str), `all_users` (bool), `state_filter` (str) | `Iterator[Job]` |

### Data Ingestion and Extraction (Load/Extract Jobs)

| Method | Summary | Input Parameters | Output |
| :--- | :--- | :--- | :--- |
| `load_table_from_uri` | Loads data into a table from Google Cloud Storage. | `source_uris` (Union[str, Sequence[str]]), `destination` (Table/TableReference/str), `job_config` (LoadJobConfig) | `LoadJob` |
| `load_table_from_dataframe`| Loads data from a pandas DataFrame. | `dataframe` (pd.DataFrame), `destination` (Table/TableReference/str), `job_config` (LoadJobConfig) | `LoadJob` |
| `load_table_from_file` | Loads data from a local file object. | `file_obj` (IO[bytes]), `destination` (Table/TableReference/str), `job_config` (LoadJobConfig) | `LoadJob` |
| `extract_table` | Extracts table data to Google Cloud Storage. | `source` (Table/TableReference/str), `destination_uris` (Union[str, Sequence[str]]), `job_config` (ExtractJobConfig) | `ExtractJob` |
| `copy_table` | Copies one or more source tables to a destination table. | `sources` (Union[Table, Sequence[Table]]), `destination` (Table/TableReference/str), `job_config` (CopyJobConfig) | `CopyJob` |

### Data Manipulation (Streaming)

| Method | Summary | Input Parameters | Output |
| :--- | :--- | :--- | :--- |
| `insert_rows` | Inserts rows into a table via the streaming API. | `table` (Table/TableReference/str), `rows` (Sequence[Union[Tuple, Dict]]) | `Sequence[Dict]` (errors) |
| `insert_rows_json` | Inserts JSON rows into a table via the streaming API. | `table` (Table/TableReference/str), `json_rows` (Sequence[Dict]) | `Sequence[Dict]` (errors) |
| `list_rows` | Retrieves table data page by page. | `table` (Table/TableReference/str), `max_results` (int), `selected_fields` (Sequence[SchemaField]) | `RowIterator` |

### Routine (Stored Procedure/UDF) Management

| Method | Summary | Input Parameters | Output |
| :--- | :--- | :--- | :--- |
| `create_routine` | Creates a new routine (e.g., a UDF or stored procedure). | `routine` (Routine), `exists_ok` (bool) | `Routine` |
| `get_routine` | Fetches a routine resource. | `routine_ref` (RoutineReference/str) | `Routine` |
| `update_routine` | Updates an existing routine. | `routine` (Routine), `fields` (Sequence[str]) | `Routine` |
| `delete_routine` | Deletes a routine. | `routine` (Routine/RoutineReference/str), `not_found_ok` (bool) | `None` |
| `list_routines` | Lists routines in a dataset. | `dataset` (Dataset/DatasetReference/str), `max_results` (int) | `Iterator[Routine]` |

### Model (BigQuery ML) Management

| Method | Summary | Input Parameters | Output |
| :--- | :--- | :--- | :--- |
| `get_model` | Fetches a BQML model resource. | `model_ref` (ModelReference/str) | `Model` |
| `update_model` | Updates properties of an existing BQML model. | `model` (Model), `fields` (Sequence[str]) | `Model` |
| `delete_model` | Deletes a BQML model. | `model` (Model/ModelReference/str), `not_found_ok` (bool) | `None` |
| `list_models` | Lists BQML models in a dataset. | `dataset` (Dataset/DatasetReference/str), `max_results` (int) | `Iterator[Model]` |

### IAM Policy Management

| Method | Summary | Input Parameters | Output |
| :--- | :--- | :--- | :--- |
| `get_iam_policy` | Gets the IAM policy for a table. | `table` (Table/TableReference/str) | `Policy` |
| `set_iam_policy` | Sets the IAM policy for a table. | `table` (Table/TableReference/str), `policy` (Policy) | `Policy` |

---

## Mermaid Concept Map

Here is a conceptual Mermaid diagram illustrating the relationships between the core entities in the BigQuery Python client.

```mermaid
graph TD
    subgraph Client
        A[bigquery.Client]
    end

    subgraph Resources
        B[Dataset]
        C[Table]
        D[Routine]
        E[Model]
    end

    subgraph Jobs
        F[QueryJob]
        G[LoadJob]
        H[ExtractJob]
        I[CopyJob]
    end

    subgraph Data
        J[RowIterator]
        K[Streaming Inserts]
    end

    A -- Manages --> B
    A -- Manages --> C
    A -- Manages --> D
    A -- Manages --> E

    A -- Creates/Executes --> F
    A -- Creates/Executes --> G
    A -- Creates/Executes --> H
    A -- Creates/Executes --> I

    B -- Contains --> C
    B -- Contains --> D
    B -- Contains --> E

    F -- Produces --> J
    C -- Queried by --> F
    C -- Populated by --> G
    C -- Source for --> H
    C -- Source/Destination for --> I

    C -- Fetched by --> J
    C -- Target for --> K

    style Client fill:#D6EAF8,stroke:#333,stroke-width:2px
    style Resources fill:#D5F5E3,stroke:#333,stroke-width:2px
    style Jobs fill:#FCF3CF,stroke:#333,stroke-width:2px
    style Data fill:#FADBD8,stroke:#333,stroke-width:2px