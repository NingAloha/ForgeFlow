#![allow(dead_code)]
#![allow(unused_imports)]

mod llm;
mod runtime;
mod sieves;

fn main() {
    use std::fs;
    use std::io::{self, Read};

    let mut user_input = String::new();
    if let Err(err) = io::stdin().read_to_string(&mut user_input) {
        eprintln!("failed to read stdin: {err}");
        std::process::exit(1);
    }

    let user_input = user_input.trim_end();
    if user_input.trim().is_empty() {
        eprintln!("stdin input must not be empty");
        std::process::exit(1);
    }

    match sieves::requirements::boundary::capture_domain(user_input) {
        Ok(capture_output) => {
            if let Err(err) =
                sieves::requirements::io::write_requirements_capture_output(&capture_output)
            {
                eprintln!("{err}");
                std::process::exit(1);
            }

            match fs::read_to_string(runtime::paths::REQUIREMENTS_RUNTIME_PATH) {
                Ok(runtime_json) => {
                    print!("{runtime_json}");
                }
                Err(err) => {
                    eprintln!("failed to read runtime requirements JSON: {err}");
                    std::process::exit(1);
                }
            }
        }
        Err(err) => {
            eprintln!("{err}");
            std::process::exit(1);
        }
    }
}
