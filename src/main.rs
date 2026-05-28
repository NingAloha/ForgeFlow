#![allow(dead_code)]
#![allow(unused_imports)]

mod llm;
mod mutation;
mod runtime;
mod sieves;

use anyhow::Result;

fn main() -> anyhow::Result<()> {
    sieves::requirements::scope::application_boundary::run_application_boundary_scope()
}
