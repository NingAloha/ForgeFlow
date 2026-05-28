use serde::{Deserialize, Serialize};

pub const EXPECTED_ARTIFACT_TYPE: &str = "requirements";
pub const EXPECTED_SCHEMA_VERSION: &str = "0.1";

pub const ALLOWED_MATURITY: &[&str] = &[
    "intent",
    "scope",
    "capability",
    "requirement",
    "review_ready",
];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RequirementsArtifact {
    pub artifact_type: String,
    pub schema_version: String,
    pub maturity: String,

    pub intent: Intent,
    pub product: Product,
    pub scope: Scope,

    pub functional_requirements: Vec<serde_json::Value>,
    pub non_functional_requirements: Vec<serde_json::Value>,
    pub external_interfaces: Vec<serde_json::Value>,
    pub data_requirements: Vec<serde_json::Value>,

    pub pending_clarifications: Vec<PendingClarification>,
    pub inconsistencies: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PendingClarification {
    pub id: String,
    pub target_path: Vec<String>,
    pub question: String,
    pub sieve: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Intent {
    pub raw_input: String,
    pub goal: String,
    pub domain: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Product {
    pub target_users: Vec<String>,
    pub application_type: Vec<String>,
    pub target_platforms: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Scope {
    pub capability_categories: Vec<String>,
    pub constraints: Vec<String>,
    pub non_goals: Vec<String>,
}
