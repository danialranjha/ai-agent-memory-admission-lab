        let mut output = String::new();

        if let Some(ref header) = options.header {
            if !header.is_empty() {
                output.push_str(header);
                output.push('\n');
            }
        }

        let mut current_token_estimate = estimate_tokens(&output);

        for item in response.items {
            let kind_str = format!("{:?}", item.memory.kind).to_lowercase();
            let line = options
                .template
                .replace("{kind}", &kind_str)
                .replace("{content}", &item.memory.content)
                .replace("{score:.2}", &format!("{:.2}", item.score))
                .replace("{score}", &format!("{:.4}", item.score));

            let line_tokens = estimate_tokens(&line);
            if current_token_estimate + line_tokens > options.max_tokens {
                break;
            }

            output.push_str(&line);
            output.push('\n');
            current_token_estimate += line_tokens;
        }

        if let Some(ref footer) = options.footer {
            if !footer.is_empty() {
                let footer_tokens = estimate_tokens(footer);
                if current_token_estimate + footer_tokens <= options.max_tokens {
                    output.push_str(footer);
                }
            }
        }

        Ok(output)
