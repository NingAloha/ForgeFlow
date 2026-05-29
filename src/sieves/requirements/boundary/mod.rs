pub mod core_approach;
pub mod domain;
pub mod preview;
pub mod problem;

pub use core_approach::capture_core_approach_from_context;
pub use domain::capture_domain;
pub use preview::build_boundary_preview;
pub use preview::is_candidate_complete;
pub use preview::merge_domain_and_problem_candidate;
pub use problem::capture_problem;
pub use problem::capture_problem_from_context;
