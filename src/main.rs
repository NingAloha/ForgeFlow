#![allow(dead_code)]
#![allow(unused_imports)]

mod llm;
mod mutation;
mod runtime;
mod sieves;

use anyhow::Result;

fn main() -> Result<()> {
    sieves::requirements::scope::target_users::run_target_users_scope()
}
