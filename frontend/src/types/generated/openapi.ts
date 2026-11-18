export interface paths {
  "/api/v1/health": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Health */
    get: operations["health_api_v1_health_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/stages": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Stages */
    get: operations["stages_api_v1_stages_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Create */
    post: operations["create_api_v1_sessions_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Read */
    get: operations["read_api_v1_sessions__session_id__get"];
    put?: never;
    post?: never;
    /** Close */
    delete: operations["close_api_v1_sessions__session_id__delete"];
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/scope": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Scope */
    get: operations["get_scope_api_v1_sessions__session_id__scope_get"];
    /** Scope */
    put: operations["scope_api_v1_sessions__session_id__scope_put"];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/events": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Events */
    get: operations["events_api_v1_sessions__session_id__events_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/sources/sample": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Sample */
    post: operations["sample_api_v1_sessions__session_id__sources_sample_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/sources/postgres": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Postgres */
    post: operations["postgres_api_v1_sessions__session_id__sources_postgres_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/sources/upload": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Upload */
    post: operations["upload_api_v1_sessions__session_id__sources_upload_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/sources": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Status */
    get: operations["status_api_v1_sessions__session_id__sources_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/metadata/extract": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Run Extract */
    post: operations["run_extract_api_v1_sessions__session_id__metadata_extract_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/metadata": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Catalog */
    get: operations["catalog_api_v1_sessions__session_id__metadata_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/metadata/tables": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Tables */
    get: operations["tables_api_v1_sessions__session_id__metadata_tables_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/metadata/columns": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Columns */
    get: operations["columns_api_v1_sessions__session_id__metadata_columns_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/metadata/preview": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Preview */
    get: operations["preview_api_v1_sessions__session_id__metadata_preview_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/metadata/analyze": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Analyze */
    post: operations["analyze_api_v1_sessions__session_id__metadata_analyze_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/metadata/analysis": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Analysis */
    get: operations["get_analysis_api_v1_sessions__session_id__metadata_analysis_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/draft": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Draft */
    get: operations["get_draft_api_v1_sessions__session_id__ontology_draft_get"];
    /** Replace Draft */
    put: operations["replace_draft_api_v1_sessions__session_id__ontology_draft_put"];
    /** Draft */
    post: operations["draft_api_v1_sessions__session_id__ontology_draft_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/draft/revert": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Revert */
    post: operations["revert_api_v1_sessions__session_id__ontology_draft_revert_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/draft/save": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Save */
    post: operations["save_api_v1_sessions__session_id__ontology_draft_save_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/classes": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Add Class */
    post: operations["add_class_api_v1_sessions__session_id__ontology_classes_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/classes/{class_name}/attributes": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    /** Attributes */
    put: operations["attributes_api_v1_sessions__session_id__ontology_classes__class_name__attributes_put"];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/classes/{class_name}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    post?: never;
    /** Remove Class */
    delete: operations["remove_class_api_v1_sessions__session_id__ontology_classes__class_name__delete"];
    options?: never;
    head?: never;
    /** Rename */
    patch: operations["rename_api_v1_sessions__session_id__ontology_classes__class_name__patch"];
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/relationships": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Add Relationship */
    post: operations["add_relationship_api_v1_sessions__session_id__ontology_relationships_post"];
    /** Remove Relationship */
    delete: operations["remove_relationship_api_v1_sessions__session_id__ontology_relationships_delete"];
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/suggestions": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Suggestions */
    get: operations["get_suggestions_api_v1_sessions__session_id__ontology_suggestions_get"];
    put?: never;
    /** Suggestions */
    post: operations["suggestions_api_v1_sessions__session_id__ontology_suggestions_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/suggestions/skip": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Skip */
    post: operations["skip_api_v1_sessions__session_id__ontology_suggestions_skip_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/review/preview": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Preview */
    post: operations["preview_api_v1_sessions__session_id__ontology_review_preview_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/review": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Apply Review */
    post: operations["apply_review_api_v1_sessions__session_id__ontology_review_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/validate": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Validate */
    post: operations["validate_api_v1_sessions__session_id__ontology_validate_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/validation": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Validation Result */
    get: operations["validation_result_api_v1_sessions__session_id__ontology_validation_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/approve": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Approve */
    post: operations["approve_api_v1_sessions__session_id__ontology_approve_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/versions": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Versions */
    get: operations["list_versions_api_v1_sessions__session_id__ontology_versions_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/versions/{version}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Version */
    get: operations["get_version_api_v1_sessions__session_id__ontology_versions__version__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/versions/{version}/rollback": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Rollback */
    post: operations["rollback_api_v1_sessions__session_id__ontology_versions__version__rollback_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/use-approved": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Use Approved */
    post: operations["use_approved_api_v1_sessions__session_id__ontology_use_approved_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/ontology/audit": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Audit */
    get: operations["audit_api_v1_sessions__session_id__ontology_audit_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/builds": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Start */
    post: operations["start_api_v1_sessions__session_id__builds_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/builds/status": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Status */
    get: operations["status_api_v1_sessions__session_id__builds_status_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/builds/stages/{stage}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Result */
    get: operations["result_api_v1_sessions__session_id__builds_stages__stage__get"];
    put?: never;
    /** Stage */
    post: operations["stage_api_v1_sessions__session_id__builds_stages__stage__post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/builds/extracted-rows": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Extracted */
    get: operations["extracted_api_v1_sessions__session_id__builds_extracted_rows_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/builds/cleaning/{kind}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Cleaning */
    get: operations["cleaning_api_v1_sessions__session_id__builds_cleaning__kind__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/graphs/snapshots": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Snapshots */
    get: operations["snapshots_api_v1_sessions__session_id__graphs_snapshots_get"];
    put?: never;
    /** Save Snapshot */
    post: operations["save_snapshot_api_v1_sessions__session_id__graphs_snapshots_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/graphs/snapshots/{build_id}/current": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Promote */
    post: operations["promote_api_v1_sessions__session_id__graphs_snapshots__build_id__current_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/graphs/snapshots/{build_id}/download/{artifact}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Download */
    get: operations["download_api_v1_sessions__session_id__graphs_snapshots__build_id__download__artifact__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/graphs/data": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Data */
    get: operations["data_api_v1_sessions__session_id__graphs_data_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/graphs/nodes": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Nodes */
    get: operations["nodes_api_v1_sessions__session_id__graphs_nodes_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/graphs/node": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Node */
    get: operations["node_api_v1_sessions__session_id__graphs_node_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/graphs/path": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Path */
    get: operations["path_api_v1_sessions__session_id__graphs_path_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/graphs/metrics": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Metrics */
    get: operations["metrics_api_v1_sessions__session_id__graphs_metrics_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
    /** AIRequest */
    AIRequest: {
      /** Actor */
      actor: string;
      /**
       * Use Groq
       * @default false
       */
      use_groq: boolean;
      /**
       * Include Samples
       * @default false
       */
      include_samples: boolean;
      /** Allowed Tables */
      allowed_tables?: string[] | null;
    };
    /** ActorRequest */
    ActorRequest: {
      /** Actor */
      actor: string;
    };
    /** ApiAttribute */
    ApiAttribute: {
      /** Name */
      name: string;
      data_type: components["schemas"]["DataType"];
      /**
       * Required
       * @default false
       */
      required: boolean;
      /** Source Column */
      source_column?: string | null;
      /** Normalize */
      normalize?: ("trim" | "lower" | "upper" | "title") | null;
      /**
       * Pii
       * @default false
       */
      pii: boolean;
      /**
       * Description
       * @default
       */
      description: string;
      /** @default manual */
      origin: components["schemas"]["Origin"];
    };
    /** ApiClass */
    ApiClass: {
      /** Name */
      name: string;
      /**
       * Description
       * @default
       */
      description: string;
      /** Category */
      category?: string | null;
      /** Attributes */
      attributes?: components["schemas"]["ApiAttribute"][];
      mapping?: components["schemas"]["ApiClassMapping"] | null;
      /** @default manual */
      origin: components["schemas"]["Origin"];
    };
    /** ApiClassMapping */
    ApiClassMapping: {
      /** Source Table */
      source_table: string;
      /** Key Columns */
      key_columns: string[];
      /** Resolution Columns */
      resolution_columns?: string[];
      /** Watermark Column */
      watermark_column?: string | null;
    };
    /** ApiOntology */
    ApiOntology: {
      /** Ontology Id */
      ontology_id: string;
      /** Namespace */
      namespace: string;
      /** Name */
      name: string;
      /**
       * Version
       * @default 1
       */
      version: number;
      /** Parent Version */
      parent_version?: number | null;
      /** @default draft */
      status: components["schemas"]["OntologyStatus"];
      /** Classes */
      classes?: components["schemas"]["ApiClass"][];
      /** Relationships */
      relationships?: components["schemas"]["ApiRelationship"][];
      /** Created By */
      created_by: string;
      /** Created At */
      created_at?: string;
      /** Approved By */
      approved_by?: string | null;
      /**
       * Change Note
       * @default
       */
      change_note: string;
    };
    /** ApiRelationship */
    ApiRelationship: {
      /** Name */
      name: string;
      /** Source Class */
      source_class: string;
      /** Target Class */
      target_class: string;
      cardinality: components["schemas"]["Cardinality"];
      /**
       * Directed
       * @default true
       */
      directed: boolean;
      /**
       * Required
       * @default false
       */
      required: boolean;
      /**
       * Allow Cycles
       * @default true
       */
      allow_cycles: boolean;
      /**
       * Multi Edge
       * @default false
       */
      multi_edge: boolean;
      /** Properties */
      properties?: components["schemas"]["ApiAttribute"][];
      mapping?: components["schemas"]["ApiRelationshipMapping"] | null;
      /**
       * Description
       * @default
       */
      description: string;
      /** @default manual */
      origin: components["schemas"]["Origin"];
    };
    /** ApiRelationshipMapping */
    ApiRelationshipMapping: {
      /**
       * Kind
       * @enum {string}
       */
      kind: "foreign_key" | "join_table";
      /** Table */
      table: string;
      /** Source Key Columns */
      source_key_columns: string[];
      /** Target Key Columns */
      target_key_columns: string[];
      /** Property Columns */
      property_columns?: string[];
      /** Watermark Column */
      watermark_column?: string | null;
    };
    /** ApprovalRequest */
    ApprovalRequest: {
      /** Author */
      author: string;
      /** Reviewer */
      reviewer: string;
    };
    /** AttributeDef */
    AttributeDef: {
      /** Name */
      name: string;
      data_type: components["schemas"]["DataType"];
      /**
       * Required
       * @default false
       */
      required: boolean;
      /** Source Column */
      source_column?: string | null;
      /** Normalize */
      normalize?: ("trim" | "lower" | "upper" | "title") | null;
      /**
       * Pii
       * @default false
       */
      pii: boolean;
      /**
       * Description
       * @default
       */
      description: string;
      /** @default manual */
      origin: components["schemas"]["Origin"];
    };
    /** AttributesRequest */
    AttributesRequest: {
      /** Attributes */
      attributes: components["schemas"]["ApiAttribute"][];
    };
    /** BuildRequest */
    BuildRequest: {
      /**
       * Batch Size
       * @default 5000
       */
      batch_size: number;
      /** Business Rules */
      business_rules?: {
        [key: string]: components["schemas"]["Rule"][];
      } | null;
    };
    /**
     * Cardinality
     * @enum {string}
     */
    Cardinality: "1:1" | "1:N" | "N:1" | "M:N";
    /** ClassDef */
    ClassDef: {
      /** Name */
      name: string;
      /**
       * Description
       * @default
       */
      description: string;
      /** Category */
      category?: string | null;
      /**
       * Attributes
       * @default []
       */
      attributes: components["schemas"]["AttributeDef"][];
      mapping?: components["schemas"]["ClassMapping"] | null;
      /** @default manual */
      origin: components["schemas"]["Origin"];
    };
    /** ClassMapping */
    ClassMapping: {
      /** Source Table */
      source_table: string;
      /** Key Columns */
      key_columns: string[];
      /**
       * Resolution Columns
       * @default []
       */
      resolution_columns: string[];
      /** Watermark Column */
      watermark_column?: string | null;
    };
    /** ClassRequest */
    ClassRequest: {
      definition: components["schemas"]["ApiClass"];
    };
    /** ColumnInfo */
    ColumnInfo: {
      /** Name */
      name: string;
      /** Pg Type */
      pg_type: string;
      /**
       * Nullable
       * @default true
       */
      nullable: boolean;
      /**
       * Source Header
       * @default
       */
      source_header: string;
    };
    /**
     * DataType
     * @enum {string}
     */
    DataType:
      | "string"
      | "integer"
      | "float"
      | "decimal"
      | "boolean"
      | "date"
      | "datetime"
      | "json";
    /** Decision */
    Decision: {
      /**
       * Action
       * @enum {string}
       */
      action: "approve" | "edit" | "reject";
      /** Payload */
      payload?: {
        [key: string]: unknown;
      } | null;
    };
    /** DraftRequest */
    DraftRequest: {
      /**
       * Mode
       * @enum {string}
       */
      mode: "new" | "template" | "schema";
      /**
       * Ontology Id
       * @default retail
       */
      ontology_id: string;
      /**
       * Namespace
       * @default com.example.retail
       */
      namespace: string;
      /**
       * Name
       * @default Retail Knowledge Graph
       */
      name: string;
      /**
       * Author
       * @default data.modeller
       */
      author: string;
    };
    /** ForeignKey */
    ForeignKey: {
      /** Columns */
      columns: string[];
      /** Ref Table */
      ref_table: string;
      /** Ref Columns */
      ref_columns: string[];
    };
    /** GraphEdge */
    GraphEdge: {
      /** Source */
      source: string;
      /** Target */
      target: string;
      /** Key */
      key: string;
      /** Properties */
      properties: {
        [key: string]: unknown;
      };
    };
    /** GraphNode */
    GraphNode: {
      /** Id */
      id: string;
      /** Properties */
      properties: {
        [key: string]: unknown;
      };
    };
    /** GraphView */
    GraphView: {
      /** Nodes */
      nodes: components["schemas"]["GraphNode"][];
      /** Edges */
      edges: components["schemas"]["GraphEdge"][];
      /** Total Nodes */
      total_nodes: number;
      /** Total Edges */
      total_edges: number;
      /** Truncated */
      truncated: boolean;
    };
    /** HTTPValidationError */
    HTTPValidationError: {
      /** Detail */
      detail?: components["schemas"]["ValidationError"][];
    };
    /** Ontology */
    Ontology: {
      /** Ontology Id */
      ontology_id: string;
      /** Namespace */
      namespace: string;
      /** Name */
      name: string;
      /**
       * Version
       * @default 1
       */
      version: number;
      /** Parent Version */
      parent_version?: number | null;
      /** @default draft */
      status: components["schemas"]["OntologyStatus"];
      /**
       * Classes
       * @default []
       */
      classes: components["schemas"]["ClassDef"][];
      /**
       * Relationships
       * @default []
       */
      relationships: components["schemas"]["RelationshipDef"][];
      /**
       * Created By
       * @default system
       */
      created_by: string;
      /** Created At */
      created_at?: string;
      /** Approved By */
      approved_by?: string | null;
      /**
       * Change Note
       * @default
       */
      change_note: string;
    };
    /** OntologyRequest */
    OntologyRequest: {
      ontology: components["schemas"]["ApiOntology"];
    };
    /**
     * OntologyStatus
     * @enum {string}
     */
    OntologyStatus:
      "draft" | "pending_review" | "approved" | "rejected" | "superseded";
    /**
     * Origin
     * @enum {string}
     */
    Origin: "manual" | "ai" | "hybrid";
    /** Page[dict] */
    Page_dict_: {
      /** Items */
      items: {
        [key: string]: unknown;
      }[];
      /** Total */
      total: number;
      /** Offset */
      offset: number;
      /** Limit */
      limit: number;
    };
    /** PostgresRequest */
    PostgresRequest: {
      /** Host */
      host: string;
      /**
       * Port
       * @default 5432
       */
      port: number;
      /** Dbname */
      dbname: string;
      /** User */
      user: string;
      /**
       * Password
       * Format: password
       */
      password: string;
      /**
       * Sslmode
       * @default prefer
       * @enum {string}
       */
      sslmode:
        | "disable"
        | "allow"
        | "prefer"
        | "require"
        | "verify-ca"
        | "verify-full";
      /** Schemas */
      schemas?: string[];
    };
    /** RelationshipDef */
    RelationshipDef: {
      /** Name */
      name: string;
      /** Source Class */
      source_class: string;
      /** Target Class */
      target_class: string;
      cardinality: components["schemas"]["Cardinality"];
      /**
       * Directed
       * @default true
       */
      directed: boolean;
      /**
       * Required
       * @default false
       */
      required: boolean;
      /**
       * Allow Cycles
       * @default true
       */
      allow_cycles: boolean;
      /**
       * Multi Edge
       * @default false
       */
      multi_edge: boolean;
      /**
       * Properties
       * @default []
       */
      properties: components["schemas"]["AttributeDef"][];
      mapping?: components["schemas"]["RelationshipMapping"] | null;
      /**
       * Description
       * @default
       */
      description: string;
      /** @default manual */
      origin: components["schemas"]["Origin"];
    };
    /**
     * RelationshipMapping
     * @description Every relationship is read from ONE table whose rows are edges.
     */
    RelationshipMapping: {
      /**
       * Kind
       * @enum {string}
       */
      kind: "foreign_key" | "join_table";
      /** Table */
      table: string;
      /** Source Key Columns */
      source_key_columns: string[];
      /** Target Key Columns */
      target_key_columns: string[];
      /**
       * Property Columns
       * @default []
       */
      property_columns: string[];
      /** Watermark Column */
      watermark_column?: string | null;
    };
    /** RelationshipRequest */
    RelationshipRequest: {
      definition: components["schemas"]["ApiRelationship"];
    };
    /** RenameRequest */
    RenameRequest: {
      /** Name */
      name: string;
    };
    /** Result[GraphView] */
    Result_GraphView_: {
      data: components["schemas"]["GraphView"];
    };
    /** Result[Ontology] */
    Result_Ontology_: {
      data: components["schemas"]["Ontology"];
    };
    /** Result[Page[dict]] */
    Result_Page_dict__: {
      data: components["schemas"]["Page_dict_"];
    };
    /** Result[SchemaCatalog] */
    Result_SchemaCatalog_: {
      data: components["schemas"]["SchemaCatalog"];
    };
    /** Result[SessionView] */
    Result_SessionView_: {
      data: components["schemas"]["SessionView"];
    };
    /** Result[Union[dict, NoneType]] */
    Result_Union_dict__NoneType__: {
      /** Data */
      data: {
        [key: string]: unknown;
      } | null;
    };
    /** Result[dict] */
    Result_dict_: {
      /** Data */
      data: {
        [key: string]: unknown;
      };
    };
    /** Result[list[ReviewItem]] */
    Result_list_ReviewItem__: {
      /** Data */
      data: components["schemas"]["ReviewItem"][];
    };
    /** Result[list[dict]] */
    Result_list_dict__: {
      /** Data */
      data: {
        [key: string]: unknown;
      }[];
    };
    /** ReviewItem */
    ReviewItem: {
      /** Item Id */
      item_id: string;
      /**
       * Kind
       * @enum {string}
       */
      kind: "class" | "relationship" | "attribute" | "duplicate";
      /** Label */
      label: string;
      /** Payload */
      payload: {
        [key: string]: unknown;
      };
      /** Confidence */
      confidence: number;
      /** Rationale */
      rationale: string;
      /**
       * Status
       * @enum {string}
       */
      status: "valid" | "invalid" | "needs_review";
      /**
       * Problems
       * @default []
       */
      problems: string[];
    };
    /** ReviewRequest */
    ReviewRequest: {
      /** Actor */
      actor: string;
      /** Decisions */
      decisions?: {
        [key: string]: components["schemas"]["Decision"];
      };
      /** Acyclic Relationships */
      acyclic_relationships?: string[];
      /** Watermark Column */
      watermark_column?: string | null;
    };
    /** Rule */
    Rule: {
      /** Column */
      column: string;
      /**
       * Rule
       * @enum {string}
       */
      rule: "non_negative" | "allowed_values";
      /** Values */
      values?: string[] | null;
    };
    /** SchemaCatalog */
    SchemaCatalog: {
      /** Tables */
      tables: {
        [key: string]: components["schemas"]["TableInfo"];
      };
      /**
       * Source Name
       * @default
       */
      source_name: string;
      /**
       * Extracted At
       * @default
       */
      extracted_at: string;
    };
    /** ScopeRequest */
    ScopeRequest: {
      /** Project */
      project: string;
      /** Business Questions */
      business_questions: string[];
      /** Tables In Scope */
      tables_in_scope?: string[];
      /** Sensitive Columns */
      sensitive_columns?: string[];
      /** Users */
      users?: string[];
      /** Later List */
      later_list?: string[];
    };
    /** SessionCreate */
    SessionCreate: {
      /** Name */
      name: string;
    };
    /** SessionView */
    SessionView: {
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Name */
      name: string;
      /** Completed Stages */
      completed_stages: number[];
      /** Source Version */
      source_version: number;
      /** Job */
      job: {
        [key: string]: unknown;
      } | null;
      /** Expires In Seconds */
      expires_in_seconds: number;
    };
    /** SnapshotRequest */
    SnapshotRequest: {
      /**
       * Load Neo4J
       * @default false
       */
      load_neo4j: boolean;
    };
    /** TableInfo */
    TableInfo: {
      /** Name */
      name: string;
      /** Columns */
      columns: {
        [key: string]: components["schemas"]["ColumnInfo"];
      };
      /**
       * Primary Key
       * @default []
       */
      primary_key: string[];
      /**
       * Foreign Keys
       * @default []
       */
      foreign_keys: components["schemas"]["ForeignKey"][];
      /**
       * Unique Constraints
       * @default []
       */
      unique_constraints: string[][];
      /** Row Estimate */
      row_estimate?: number | null;
    };
    /** ValidationError */
    ValidationError: {
      /** Location */
      loc: (string | number)[];
      /** Message */
      msg: string;
      /** Error Type */
      type: string;
      /** Input */
      input?: unknown;
      /** Context */
      ctx?: Record<string, never>;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
  health_api_v1_health_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
    };
  };
  stages_api_v1_stages_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_list_dict__"];
        };
      };
    };
  };
  create_api_v1_sessions_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["SessionCreate"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_SessionView_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  read_api_v1_sessions__session_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_SessionView_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  close_api_v1_sessions__session_id__delete: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      204: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  get_scope_api_v1_sessions__session_id__scope_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Union_dict__NoneType__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  scope_api_v1_sessions__session_id__scope_put: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ScopeRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  events_api_v1_sessions__session_id__events_get: {
    parameters: {
      query?: {
        offset?: number;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Page_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  sample_api_v1_sessions__session_id__sources_sample_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  postgres_api_v1_sessions__session_id__sources_postgres_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["PostgresRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  upload_api_v1_sessions__session_id__sources_upload_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "multipart/form-data": {
          files: string[];
        };
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  status_api_v1_sessions__session_id__sources_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  run_extract_api_v1_sessions__session_id__metadata_extract_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_SchemaCatalog_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  catalog_api_v1_sessions__session_id__metadata_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_SchemaCatalog_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  tables_api_v1_sessions__session_id__metadata_tables_get: {
    parameters: {
      query?: {
        offset?: number;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Page_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  columns_api_v1_sessions__session_id__metadata_columns_get: {
    parameters: {
      query: {
        table: string;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_list_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  preview_api_v1_sessions__session_id__metadata_preview_get: {
    parameters: {
      query: {
        table: string;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_list_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  analyze_api_v1_sessions__session_id__metadata_analyze_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  get_analysis_api_v1_sessions__session_id__metadata_analysis_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_list_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  get_draft_api_v1_sessions__session_id__ontology_draft_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  replace_draft_api_v1_sessions__session_id__ontology_draft_put: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["OntologyRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  draft_api_v1_sessions__session_id__ontology_draft_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["DraftRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  revert_api_v1_sessions__session_id__ontology_draft_revert_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  save_api_v1_sessions__session_id__ontology_draft_save_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  add_class_api_v1_sessions__session_id__ontology_classes_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ClassRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  attributes_api_v1_sessions__session_id__ontology_classes__class_name__attributes_put: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        class_name: string;
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AttributesRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  remove_class_api_v1_sessions__session_id__ontology_classes__class_name__delete: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        class_name: string;
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  rename_api_v1_sessions__session_id__ontology_classes__class_name__patch: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        class_name: string;
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["RenameRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  add_relationship_api_v1_sessions__session_id__ontology_relationships_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["RelationshipRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  remove_relationship_api_v1_sessions__session_id__ontology_relationships_delete: {
    parameters: {
      query: {
        key: string;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  get_suggestions_api_v1_sessions__session_id__ontology_suggestions_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  suggestions_api_v1_sessions__session_id__ontology_suggestions_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AIRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_list_ReviewItem__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  skip_api_v1_sessions__session_id__ontology_suggestions_skip_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  preview_api_v1_sessions__session_id__ontology_review_preview_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ReviewRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  apply_review_api_v1_sessions__session_id__ontology_review_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ReviewRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  validate_api_v1_sessions__session_id__ontology_validate_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  validation_result_api_v1_sessions__session_id__ontology_validation_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  approve_api_v1_sessions__session_id__ontology_approve_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ApprovalRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  list_versions_api_v1_sessions__session_id__ontology_versions_get: {
    parameters: {
      query: {
        ontology_id: string;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_list_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  get_version_api_v1_sessions__session_id__ontology_versions__version__get: {
    parameters: {
      query: {
        ontology_id: string;
      };
      header?: never;
      path: {
        version: number;
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  rollback_api_v1_sessions__session_id__ontology_versions__version__rollback_post: {
    parameters: {
      query: {
        ontology_id: string;
      };
      header?: never;
      path: {
        version: number;
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ActorRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  use_approved_api_v1_sessions__session_id__ontology_use_approved_post: {
    parameters: {
      query: {
        ontology_id: string;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Ontology_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  audit_api_v1_sessions__session_id__ontology_audit_get: {
    parameters: {
      query: {
        ontology_id: string;
        offset?: number;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Page_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  start_api_v1_sessions__session_id__builds_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["BuildRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      202: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  status_api_v1_sessions__session_id__builds_status_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Union_dict__NoneType__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  result_api_v1_sessions__session_id__builds_stages__stage__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        stage: number;
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  stage_api_v1_sessions__session_id__builds_stages__stage__post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        stage: number;
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["BuildRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  extracted_api_v1_sessions__session_id__builds_extracted_rows_get: {
    parameters: {
      query: {
        table: string;
        offset?: number;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Page_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  cleaning_api_v1_sessions__session_id__builds_cleaning__kind__get: {
    parameters: {
      query?: {
        offset?: number;
        limit?: number;
      };
      header?: never;
      path: {
        kind: string;
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Page_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  snapshots_api_v1_sessions__session_id__graphs_snapshots_get: {
    parameters: {
      query: {
        ontology_id: string;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_list_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  save_snapshot_api_v1_sessions__session_id__graphs_snapshots_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["SnapshotRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  promote_api_v1_sessions__session_id__graphs_snapshots__build_id__current_post: {
    parameters: {
      query: {
        ontology_id: string;
      };
      header?: never;
      path: {
        build_id: string;
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  download_api_v1_sessions__session_id__graphs_snapshots__build_id__download__artifact__get: {
    parameters: {
      query: {
        ontology_id: string;
      };
      header?: never;
      path: {
        build_id: string;
        artifact:
          | "graph.json.gz"
          | "graph.graphml"
          | "manifest.json"
          | "quarantine.json";
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  data_api_v1_sessions__session_id__graphs_data_get: {
    parameters: {
      query?: {
        ontology_id?: string | null;
        build_id?: string | null;
        limit?: number;
        edge_limit?: number;
        labels?: string[] | null;
        focus?: string | null;
        hops?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_GraphView_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  nodes_api_v1_sessions__session_id__graphs_nodes_get: {
    parameters: {
      query?: {
        ontology_id?: string | null;
        build_id?: string | null;
        search?: string;
        label?: string | null;
        offset?: number;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_Page_dict__"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  node_api_v1_sessions__session_id__graphs_node_get: {
    parameters: {
      query: {
        node_id: string;
        ontology_id?: string | null;
        build_id?: string | null;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  path_api_v1_sessions__session_id__graphs_path_get: {
    parameters: {
      query: {
        source: string;
        target: string;
        ontology_id?: string | null;
        build_id?: string | null;
        max_hops?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  metrics_api_v1_sessions__session_id__graphs_metrics_get: {
    parameters: {
      query?: {
        ontology_id?: string | null;
        build_id?: string | null;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Result_dict_"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
}
