def generate_xml_codechunk(item_ids, profile_name="NQify", chunk_name="ReduceAndCombine"):
    # Convert item IDs to strings with proper formatting
    items_str = ", ".join(str(id) for id in item_ids)

    xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<Profile>
    <name>{profile_name}</name>
    <Order>
        <RunCode Name="{chunk_name}"/>
    </Order>
    <CodeChunks>
        <CodeChunk Name="{chunk_name}">
            <![CDATA[
// Settings
const string ChunkName = "ItemQualityReducer";

// Logging setup
var log = new LlamaLibrary.Logging.LLogger(ChunkName, System.Windows.Media.Colors.Pink);

// List of item IDs to process
var itemIds = new System.Collections.Generic.List<int> {{ {items_str} }};

foreach (var itemId in itemIds) {{
    log.Information($"Processing item {{itemId}}");
    await LlamaLibrary.Helpers.InventoryHelpers.LowerQualityAndCombine(itemId);
}}

log.Information("Finished processing all items");
            ]]>
        </CodeChunk>
    </CodeChunks>
</Profile>"""

    return xml_template


def process_json_to_xml(filepath):
    import json
    # Read JSON from file
    with open(filepath, 'r') as f:
        data = json.load(f)

    # Extract item IDs
    item_ids = [item['Item'] for item in data]

    # Generate XML
    return generate_xml_codechunk(item_ids)

# print(process_json_to_xml("../Lisbeth/Quest Items/V2Part1Intermediates.json"))

# print(process_json_to_xml("../Lisbeth/Quest Items/V2Part2Intermediates.json"))

print(process_json_to_xml("../Lisbeth/Quest Items/V2Part3Intermediates.json"))