---
name: comment-on-docx
category: 教学辅导
subject: 跨学科
kind: 评价测评
description: >-
  给 Word(.docx)文档添加批注式反馈:按批注规范定位到具体词句,以原生 Word 批注(comment)写回原文而不改动正文,并另存副本。适合作文/论文/作业批改与文稿评审。自带读取文档 runs、起草批注、用 python-docx 程序化插入批注的脚本与指南。触发词:批改作文, 给文档加批注, Word 批注, 论文评阅, 作业反馈, 评审意见, 不改原文的修改建议; comment on docx, word comments, review feedback, add comments.
---

# Add Comments to Word Documents

## Overview

Add thoughtful stylistic and content-wise comments to Microsoft Word (.docx) documents using helper scripts that abstract the complexity of the python-docx library.

## Prerequisites

- `python-docx>=1.2.0`
- `lxml` (comes with python-docx)
- Helper scripts: `scripts/read_document_runs.py` and `scripts/docx_comment_helper.py` (bundled with this skill)
- Access to the target `.docx` file

## Custom Environment Information

<!-- Users can add information about their Python environment here -->

## Workflow

### Step 0: Read this SKILL.md file, and read the commenting guidelines in `references/commenting.md`

Make sure you read the SKILL.md file FULLY until the [SKILL.md Ends] flag at the end. Do NOT truncate this file in ANY WAY while reading it.

### Step 1: Read the Complete Document

**CRITICAL**: You MUST read the ENTIRE document before adding comments.

Run the helper script to see all runs numbered:

```bash
python scripts/read_document_runs.py "document.docx"
```

(The script is bundled with this skill — resolve the path relative to this skill's directory.)

**Output format:**
```
📊 DOCUMENT STATISTICS:
   Total runs: 7
   Total characters: 98
   Existing comments: 1
   Images: 1

🖼️  EXTRACTED IMAGES (saved to /tmp/docx_images_abc123/):
   /tmp/docx_images_abc123/image1.png (Paragraph 2, Run 5)

   ➡️  Use the Read tool to view each image file listed above for full document context.

💬 EXISTING COMMENTS:
   [Jane] (Paragraph 0) Nice title

📖 ALL RUNS (numbered for easy reference):
================================================================================

--- Paragraph 0 ---
[Run 0] My Document Title

--- Paragraph 1 ---
[Run 1] Here is a sentence. [ITALIC]
[Run 2] [EMPTY]
[Run 3] More text here.
[Run 4] Final sentence. [BOLD]

--- Paragraph 2 ---
[Run 5] [IMAGE: image1.png]
[Run 6] Figure 1: A chart showing results. [ITALIC]
================================================================================

✅ Document read complete. Total runs: 7
   (Make sure you see all runs from [Run 0] to [Run 6])

🖼️  IMPORTANT: This document contains 1 image(s).
   Read the images from /tmp/docx_images_abc123/ to understand figures and diagrams.
```

**What you're looking for:**
- The total number of runs
- All runs numbered from `[Run 0]` to `[Run N-1]`
- Formatting indicators: `[BOLD]`, `[ITALIC]`, `[EMPTY]`, `[IMAGE: filename]`
- Existing comments to avoid duplicating feedback
- **Images**: If the document contains images, the script extracts them to a temp directory and lists their paths

**Verification**: Confirm you see the final run matching `Total runs - 1`. If the output seems truncated or you don't see all runs, **STOP and report the issue**.

> **HARD STOP RULE**: If ANY part of the read output looks wrong, incomplete, or suspicious, the document has NOT been fully read. You MUST stop immediately. Do NOT draft comments, do NOT write code, do NOT skip ahead. Simply inform the user that something looks off and what it is. Do nothing else. There are NO exceptions.
>
> This includes but is not limited to:
> - Run text that ends with "..." or appears cut off
> - Existing comments that show blank/missing text (e.g. `[Author] (Paragraph 5)` with no comment content — real comments always have text)
> - Unexpected gaps, missing sections, or anything that just looks off
>
> **The spirit of this rule: if you have not read ALL of the document's content — runs, comments, images, everything — you are not ready to comment.** Proceeding without full context produces low-quality, superficial feedback and wastes the user's time. Your job is to be a careful reader first. If something looks weird in the output, it probably IS weird, and you need to stop and tell the user. Do not attempt to fix anything, do not proceed, do not draft comments. Just stop and inform the user.

#### Viewing Images

If the document contains images (figures, charts, diagrams), the read script automatically extracts them to a temp directory and lists their file paths. **After reading all the text runs**, use the Read tool to view each extracted image file. This gives you full visual context for understanding figures referenced in the text.

- Images appear in the run output as `[IMAGE: filename]` markers showing where they are positioned in the document
- The extracted image paths are listed in the "EXTRACTED IMAGES" section at the top of the output
- You can comment on text adjacent to images (e.g., captions, surrounding paragraphs) — you cannot comment directly on image-only runs since they have no text content

### Step 2: Draft Comments

Take time to formulate thoughtful, constructive comments. Open up `references/commenting.md` (bundled with this skill) for additional instructions. Re-read it in full and follow the instructions contained within. 

MAKE SURE YOU RE-READ commenting.md after you've read the entire document as a refresher. Only then should you start drafting your comments.

### Step 3: Add Comments Using `add_comments_batch`

**Always use `add_comments_batch`** to add comments. It processes comments in reverse run-ID order so that `subset_text` splits (which insert new runs) don't shift the IDs of comments that haven't been processed yet. This means you can use the run IDs straight from the read script output without worrying about offsets.

Create a Python script using the helper functions:

```python
from docx import Document
from scripts.docx_comment_helper import add_comments_batch, save_with_suffix, verify_comments
# ↑ Import from this skill's scripts/ directory — add it to sys.path if needed

# Load document
doc = Document('your_document.docx')

# Define all comments as a list of dicts
comments = [
    {"run_ids": 42, "text": "Your comment here"},
    {"run_ids": [10, 11, 12, 13], "text": "Comment on this whole section"},
    {"run_ids": 5, "subset_text": "specific phrase", "text": "Comment on just this phrase"},
]

# Add all comments (order doesn't matter — batch handles it)
successes, failures = add_comments_batch(doc, comments)
```

#### Comment dict format

Each comment dict has these keys:

| Key | Required | Description |
|-----|----------|-------------|
| `run_ids` | Yes | Single int or list of ints (global run IDs from read script) |
| `text` | Yes | The comment text |
| `subset_text` | No | Phrase to isolate within a single run. Splits the run automatically. |

#### Comment on Entire Runs (Paragraphs or Sections)

```python
# Single run
{"run_ids": 42, "text": "Your comment here"}

# Multiple consecutive runs
{"run_ids": [10, 11, 12, 13], "text": "Comment on this whole section"}
```

#### Comment on Specific Text Within a Run

```python
# Comment on just a phrase — the batch function handles the split safely
{"run_ids": 5, "subset_text": "specific phrase", "text": "Comment on just this phrase"}
```

**Important Notes:**
- Use run IDs from the read script output (`[Run 0]`, `[Run 1]`, etc.) — no manual offset adjustment needed
- Single run: `run_ids=42`
- Multiple runs: `run_ids=[10, 11, 12, 13]`
- `subset_text` only works with single runs
- Empty runs cannot be commented on (will be skipped)
- Bolded/italicized text is often already its own run
- `subset_text` matching is case-insensitive, but beware of smart quotes/special characters in Word docs — when in doubt, comment on the whole run instead

**⚠️ Multiple `subset_text` Comments on the Same Run — Use Multiple Passes:**

It's common and important to put multiple `subset_text` comments on the same run. For example, a long paragraph with no formatting changes is often a single run, and you may want to comment on several different sentences within it. Targeting specific sentences is much better than dumping all your feedback into one comment on the whole paragraph — it makes the comments easier to read and act on. Don't let the mechanics of multi-pass commenting discourage you from writing precise, well-targeted comments.

However, splitting a run with `subset_text` creates new runs and shifts IDs. So if you need N `subset_text` comments on the same run, you need N passes:

1. **First pass**: add all comments in a batch (including one `subset_text` comment per run that needs multiple)
2. **Re-read the document** using `read_document_runs.py` to get fresh run IDs
3. **Second pass**: find the target text in the new run structure and add the next round of comments
4. Repeat until all comments are placed

**Example:** Suppose run 42 is a long paragraph:
```
[Run 42] The president has broad authority to control exports. This authority derives from
the Export Administration Regulation. Chip restrictions would be a significant barrier because
most compute is US-based. Replacing chips would be difficult since manufacturers are also
covered by export controls.
```

You want to comment on three sentences. You'd need three passes:
- Pass 1: `{"run_ids": 42, "subset_text": "This authority derives from the Export Administration Regulation", "text": "A comment."}`
- Re-read document → the paragraph is now split into multiple runs with new IDs
- Pass 2: find "Chip restrictions would be a significant barrier" in the new runs, add comment
- Re-read again → pass 3: find "Replacing chips would be difficult", add comment

**⚠️ Uniqueness Requirement:**
- Each `subset_text` only needs to be unique **within its target run** (not the whole document) — the script searches only within the run identified by `run_ids`
- If the same phrase appears twice within a single run, the script will match the first occurrence
- **Best practice:** Use longer, more specific phrases to avoid ambiguity within the run

**Understanding Runs:**

A "run" is a text fragment with consistent formatting. Runs are created when:
- Formatting changes (normal → bold → normal)
- Inline styles are applied
- The document structure requires it

Example paragraph breakdown:
```
"This is normal. This is bold. This is normal again."
  ↓
[Run 0] "This is normal. "
[Run 1] "This is bold." [BOLD]
[Run 2] " This is normal again."
```

#### Recall the instruction in commenting.md: First draft the python file, then review it for any potential changes, only after the review should you run the python file and add comments.


### Step 4: Save with Standard Suffix

```python
# Save to new file
output_path = save_with_suffix(
    doc,
    'your_document.docx',
    suffix="claude commented"  # Default value
)
```

This creates: `your_document - claude commented.docx` Name your comment script [short_title]_comments.py, where [short_title] is a shortened version of the doc filename.

**Never overwrite the original file.**

**Web environment (read-only uploads):**

When running in the Claude web environment, the uploads directory (`/mnt/user-data/uploads/`) is read-only. You must specify an output directory to avoid an OSError:
```python
output_path = save_with_suffix(
    doc,
    'your_document.docx',
    output_dir='/home/claude/'
)
```

Then copy the final file to `/mnt/user-data/outputs/` for the user to download.

### Step 5: Verify Success

```python
# Verify comments were added
doc_verify = Document(output_path)
count = verify_comments(doc_verify, expected_author="Claude")

print(f"Added {count} comments successfully")
```

The verification shows:
- Total comments in document
- Number of comments from your author name
- Confirms successful addition

## Complete Example (Multi-Pass)

This example shows commenting on a document where some runs need multiple `subset_text` comments — requiring re-reads between passes.

```python
from docx import Document
from scripts.docx_comment_helper import add_comments_batch, save_with_suffix, verify_comments
# ↑ Import from this skill's scripts/ directory — add it to sys.path if needed

INPUT = 'research_post.docx'

# --- Pass 1: all comments, including one subset_text per run that needs multiple ---
doc = Document(INPUT)
pass1_comments = [
    {
        "run_ids": 0,
        "text": "Style: The title is unclear. Consider: 'How Models Generalize Reward-Seeking Goals'",
    },
    {
        "run_ids": 37,
        "text": "Emphasis: Is the bolding necessary here? It may distract from the main point.",
    },
    {
        # Run 42 is a long paragraph — we want to comment on two sentences in it.
        # First subset_text comment goes in pass 1:
        "run_ids": 42,
        "subset_text": "The AI strategizes to maximize reward",
        "text": "Word choice: 'strategizes' assumes sophisticated reasoning. Justify or soften this claim.",
    },
    {
        "run_ids": [15, 16, 17, 18],
        "text": "Structure: This paragraph is dense. Consider splitting into two.",
    },
]
add_comments_batch(doc, pass1_comments)
WORKING_COPY = save_with_suffix(doc, INPUT, output_dir='/home/claude/')  # never overwrite the original

# --- Pass 2: re-read working copy to get fresh run IDs, add remaining comments ---
# Run read_document_runs.py on the working copy to find the new run ID
# for "Replacing existing chips would be difficult" — it was in run 42 before,
# but after the split it's in a new run.
doc = Document(WORKING_COPY)
pass2_comments = [
    {
        "run_ids": 44,  # new run ID found after re-reading
        "subset_text": "Replacing existing chips would be difficult",
        "text": "Content: This claim needs support. Which manufacturers? What are the lead times?",
    },
]
add_comments_batch(doc, pass2_comments)
doc.save(WORKING_COPY)  # overwrite the working copy in /home/claude/ (not the original)

# --- Verify ---
doc_verify = Document(WORKING_COPY)
count = verify_comments(doc_verify, expected_author="Claude")
print(f"✅ Added {count} comments to {WORKING_COPY}")
```

## Common Issues

### Issue 1: Cannot read entire document

**Symptom**: Output is truncated, doesn't show all runs

**Solution**: The document may be too large. Report to user that the document is too long to process safely.

### Issue 2: Run not found

**Symptom**: `❌ Run X not found in document`

**Cause**: Run ID doesn't exist (document has fewer runs than expected)

**Solution**: Re-run the read script to get current run structure

### Issue 3: Subset text not found

**Symptom**: `❌ Text 'phrase' not found in run`

**Cause**: The text doesn't exist in that run, or there's a typo

**Solution**: Check the read script output to verify which run contains the text

### Issue 4: Empty run error

**Symptom**: `❌ All target runs are empty - cannot add comment`

**Cause**: Trying to comment on runs with no text content

**Solution**: Skip empty runs or comment on adjacent runs with text

### Issue 5: Multiple subset_text on same run fails

**Symptom**: Second `subset_text` comment on the same run fails with "Text not found in run"

**Cause**: The first `subset_text` split the run into new runs with new IDs. The original run ID no longer contains the text you're looking for.

**Solution**: Re-read the document with `read_document_runs.py` to get fresh run IDs, then add the next comment targeting the correct new run. Repeat for each additional comment. See the "Multiple `subset_text` Comments on the Same Run" section above.

## Best Practices

1. **Always read the complete document first** - Don't add comments without full context
2. **Draft comments before coding** - Think through feedback before writing code
3. **Never overwrite originals** - Always use `save_with_suffix()`
4. **Verify after adding** - Check that comments were successfully added
5. **Comment at appropriate granularity** - Apply comments to words/sentences/paragraphs as appropriate

Always follow the guideline in `references/commenting.md` when writing comments.

## Limitations

- Very large documents (>100,000 words) may be slow or fail to read completely. If you cannot read the whole document, STOP AND LET THE USER KNOW.
- Comments cannot be added to headers, footers, or within existing comments
- Nested or overlapping comments are not supported

## Helper Script Details

### scripts/read_document_runs.py
- Reads document and numbers all runs sequentially
- Shows formatting (bold, italic, empty)
- Extracts images to a temp directory and shows `[IMAGE: filename]` markers in the run output
- Lists existing comments with their paragraph locations
- Provides verification that document was read completely

### scripts/docx_comment_helper.py
- `add_comments_batch()`: **Primary interface** — takes a list of comment dicts, processes them in reverse run-ID order to avoid ID shift issues from `subset_text` splits
- `add_comment()`: Low-level interface for adding a single comment (use `add_comments_batch` instead to avoid run ID shift bugs)
- `save_with_suffix()`: Save with standard naming convention
- `verify_comments()`: Confirm comments were added successfully
- Handles run splitting automatically when using `subset_text`
- Preserves formatting when splitting runs

[SKILL.md Ends]