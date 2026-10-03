# Exact formatter evidence

15 fixed fixtures, two methods each. These are source-slice observations, not attack rates or live-agent behavior.

The ordered input for oversized_first is 48 L characters, KEEP-A, KEEP-B, budget8, template {content}, no header/footer. The upstream estimate assigns12,2,2 units.

**stop output, exact JSON string:** `""`

**continue output, exact JSON string:** `"KEEP-A\nKEEP-B\n"`

The large record is omitted by both. Continue scans the remaining list. The ordinary twin returns the same two lines in both.

| Fixture | Budget | Input IDs | Stop IDs | Continue IDs | Whole-output estimate exceeds budget (stop / continue) |
|---|---:|---|---|---|---|
|oversized_first|8|['large', 'a', 'b']|[]|['a', 'b']|False / False|
|oversized_middle|8|['a', 'large', 'b']|['a']|['a', 'b']|False / False|
|oversized_last|8|['a', 'b', 'large']|['a', 'b']|['a', 'b']|False / False|
|ordinary_twin|8|['a', 'b']|['a', 'b']|['a', 'b']|False / False|
|exact_fill|4|['a', 'b']|['a', 'b']|['a', 'b']|False / False|
|no_remaining_room|2|['a', 'b']|['a']|['a']|False / False|
|all_oversized|8|['large', 'large2']|[]|[]|False / False|
|empty|8|[]|[]|[]|False / False|
|header_consumes_room|8|['large', 'a', 'b']|[]|['a']|False / False|
|footer_is_preserved|8|['large', 'a', 'b']|[]|['a', 'b']|False / False|
|oversized_header|2|['a']|[]|[]|True / True|
|newline_estimate_limit|2|['a', 'b']|['a', 'b']|['a', 'b']|True / True|
|empty_record_limit|1|['a', 'b', 'c', 'd', 'e']|[]|[]|True / True|
|unicode_cost|4|['large', 'a', 'b']|[]|['a', 'b']|False / False|
|default_template|24|['large', 'a', 'b']|[]|['a', 'b']|False / False|

IDs here are an exact substring witness for unique non-empty fixture strings, not a general parser. Empty-record behavior is established by the exact output bytes in run.json. Whole-output estimate is an independent ceil(bytes/4) check, not an actual tokenizer. Header and newline cases expose remaining limits, not fixes supplied by this patch. Greedy continuation does not optimize relevance or prevent a full context of many small records.
