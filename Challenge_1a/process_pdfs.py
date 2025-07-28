import os
import json
from pathlib import Path
from collections import namedtuple, defaultdict
import fitz  # PyMuPDF
import re

TextSpan = namedtuple("TextSpan", ["text", "font_size", "bold", "x", "y", "width", "page_number"])

# Words that are unlikely to be headings (verbs, common words, etc.)
UNLIKELY_HEADING_WORDS = {
    # Common verbs that shouldn't be headings
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
    'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall',
    'get', 'got', 'getting', 'give', 'gave', 'given', 'go', 'went', 'gone', 'going',
    'make', 'made', 'making', 'take', 'took', 'taken', 'taking', 'come', 'came', 'coming',
    'see', 'saw', 'seen', 'seeing', 'know', 'knew', 'known', 'knowing', 'think', 'thought', 'thinking',
    'say', 'said', 'saying', 'tell', 'told', 'telling', 'ask', 'asked', 'asking',
    'find', 'found', 'finding', 'use', 'used', 'using', 'work', 'worked', 'working',
    'try', 'tried', 'trying', 'help', 'helped', 'helping', 'want', 'wanted', 'wanting',
    'need', 'needed', 'needing', 'feel', 'felt', 'feeling', 'become', 'became', 'becoming',
    'seem', 'seemed', 'seeming', 'look', 'looked', 'looking', 'turn', 'turned', 'turning',
    'keep', 'kept', 'keeping', 'put', 'putting', 'set', 'setting', 'run', 'ran', 'running',
    'move', 'moved', 'moving', 'live', 'lived', 'living', 'bring', 'brought', 'bringing',
    'happen', 'happened', 'happening', 'write', 'wrote', 'written', 'writing', 'sit', 'sat', 'sitting',
    'stand', 'stood', 'standing', 'lose', 'lost', 'losing', 'pay', 'paid', 'paying',
    'meet', 'met', 'meeting', 'include', 'included', 'including', 'continue', 'continued', 'continuing',
    'set', 'setting', 'follow', 'followed', 'following', 'stop', 'stopped', 'stopping',
    'create', 'created', 'creating', 'speak', 'spoke', 'spoken', 'speaking', 'read', 'reading',
    'allow', 'allowed', 'allowing', 'add', 'added', 'adding', 'spend', 'spent', 'spending',
    'grow', 'grew', 'grown', 'growing', 'open', 'opened', 'opening', 'walk', 'walked', 'walking',
    'win', 'won', 'winning', 'offer', 'offered', 'offering', 'remember', 'remembered', 'remembering',
    'love', 'loved', 'loving', 'consider', 'considered', 'considering', 'appear', 'appeared', 'appearing',
    'buy', 'bought', 'buying', 'wait', 'waited', 'waiting', 'serve', 'served', 'serving',
    'die', 'died', 'dying', 'send', 'sent', 'sending', 'expect', 'expected', 'expecting',
    'build', 'built', 'building', 'stay', 'stayed', 'staying', 'fall', 'fell', 'fallen', 'falling',
    'cut', 'cutting', 'reach', 'reached', 'reaching', 'kill', 'killed', 'killing',
    'remain', 'remained', 'remaining', 'suggest', 'suggested', 'suggesting', 'raise', 'raised', 'raising',
    'pass', 'passed', 'passing', 'sell', 'sold', 'selling', 'require', 'required', 'requiring',
    'report', 'reported', 'reporting', 'decide', 'decided', 'deciding', 'pull', 'pulled', 'pulling',
    
    # Common articles, prepositions, conjunctions
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
    'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'among', 'under', 'over', 'against', 'within', 'without', 'across', 'behind',
    'beyond', 'plus', 'except', 'but', 'until', 'unless', 'since', 'while', 'where', 'when',
    'why', 'how', 'what', 'which', 'who', 'whom', 'whose', 'that', 'this', 'these', 'those',
    
    # Common adverbs and adjectives that are unlikely headings
    'very', 'really', 'quite', 'rather', 'pretty', 'fairly', 'extremely', 'highly', 'completely',
    'totally', 'absolutely', 'perfectly', 'entirely', 'fully', 'hardly', 'barely', 'nearly',
    'almost', 'just', 'only', 'even', 'still', 'yet', 'already', 'soon', 'late', 'early',
    'fast', 'slow', 'quick', 'long', 'short', 'big', 'small', 'large', 'little', 'old', 'new',
    'good', 'bad', 'great', 'poor', 'high', 'low', 'right', 'wrong', 'true', 'false',
    'easy', 'hard', 'simple', 'complex', 'clear', 'unclear', 'clean', 'dirty', 'fresh', 'old',
    
    # Common pronouns
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
    'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'ours', 'theirs',
    'myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves',
    
    # Other unlikely single words
    'yes', 'no', 'ok', 'okay', 'well', 'now', 'then', 'here', 'there', 'where', 'everywhere',
    'somewhere', 'nowhere', 'anywhere', 'today', 'yesterday', 'tomorrow', 'always', 'never',
    'sometimes', 'often', 'usually', 'frequently', 'rarely', 'seldom', 'once', 'twice',
    'again', 'back', 'away', 'together', 'apart', 'alone', 'enough', 'too', 'so', 'such',
}

# Words that are commonly good headings (even if single word)
LIKELY_HEADING_WORDS = {
    # Academic/Professional terms
    'introduction', 'conclusion', 'summary', 'abstract', 'overview', 'background', 'methodology',
    'results', 'discussion', 'analysis', 'findings', 'recommendations', 'bibliography', 'references',
    'appendix', 'appendices', 'glossary', 'index', 'preface', 'acknowledgments', 'contents',
    
    # Chapter/Section indicators
    'chapter', 'section', 'part', 'unit', 'lesson', 'module', 'topic', 'subject', 'theme',
    
    # Technical terms
    'specifications', 'requirements', 'implementation', 'architecture', 'design', 'development',
    'testing', 'deployment', 'maintenance', 'troubleshooting', 'configuration', 'installation',
    'setup', 'optimization', 'performance', 'security', 'documentation', 'tutorial', 'guide',
    
    # Business terms
    'objectives', 'goals', 'strategy', 'planning', 'budget', 'resources', 'timeline', 'milestones',
    'deliverables', 'stakeholders', 'risks', 'benefits', 'costs', 'roi', 'metrics', 'kpis',
    
    # General categories
    'history', 'theory', 'practice', 'application', 'examples', 'case', 'study', 'research',
    'literature', 'review', 'survey', 'comparison', 'evaluation', 'assessment', 'framework',
    'model', 'approach', 'method', 'technique', 'procedure', 'process', 'workflow', 'steps',
    'phases', 'stages', 'levels', 'types', 'categories', 'classification', 'taxonomy',
    'principles', 'concepts', 'fundamentals', 'basics', 'advanced', 'expert', 'professional',
    'standards', 'guidelines', 'policies', 'procedures', 'protocols', 'best', 'practices',
    'trends', 'future', 'outlook', 'forecast', 'projections', 'implications', 'impact',
    'challenges', 'solutions', 'opportunities', 'threats', 'strengths', 'weaknesses',
}


def build_font_gap_stats(text_spans):
    font_gap_data = defaultdict(list)
    for span in text_spans:
        words = span.text.strip().split()
        if len(words) <= 1:
            continue
        avg_gap = span.width / (len(words) - 1)
        font_gap_data[span.font_size].append(avg_gap)

    avg_gaps = {}
    for font, gaps in font_gap_data.items():
        avg_gaps[font] = sum(gaps) / len(gaps)
    return avg_gaps


def is_likely_heading_word(word):
    """Check if a single word is likely to be a heading"""
    word_lower = word.lower().strip()
    
    # Remove common punctuation
    word_clean = re.sub(r'[^\w]', '', word_lower)
    
    # If it's in the unlikely list, it's probably not a heading
    if word_clean in UNLIKELY_HEADING_WORDS:
        return False
    
    # If it's in the likely list, it's probably a heading
    if word_clean in LIKELY_HEADING_WORDS:
        return True
    
    # Additional checks for single words
    if len(word_clean) < 3:  # Very short words are unlikely to be headings
        return False
    
    # Check if it's a proper noun (starts with capital) - more likely to be heading
    if word[0].isupper() and len(word_clean) >= 4:
        return True
    
    # Check if it's all caps (common for headings)
    if word.isupper() and len(word_clean) >= 3:
        return True
    
    # Numbers or roman numerals alone are unlikely
    if word_clean.isdigit():
        return False
    
    # If it contains digits mixed with letters, might be a section number
    if re.search(r'\d', word_clean) and re.search(r'[a-zA-Z]', word_clean):
        return True
    
    # Default: be conservative with single words
    return False


def extend_heading_span(center_span, spans_by_line, avg_gap_per_font):
    font_size = center_span.font_size
    avg_gap = avg_gap_per_font.get(font_size, 100)  # Default to a large value if missing

    line_spans = spans_by_line.get((center_span.page_number, center_span.y), [])
    line_spans = sorted(line_spans, key=lambda s: s.x)

    collected = []
    for i, span in enumerate(line_spans):
        if span == center_span:
            collected.append(span)
            # Expand left
            j = i - 1
            while j >= 0 and abs(line_spans[j+1].x - (line_spans[j].x + line_spans[j].width)) <= avg_gap * 1.3:
                collected.insert(0, line_spans[j])
                j -= 1
            # Expand right
            j = i + 1
            while j < len(line_spans) and abs(line_spans[j].x - (line_spans[j-1].x + line_spans[j-1].width)) <= avg_gap * 1.3:
                collected.append(line_spans[j])
                j += 1
            break

    combined_text = " ".join(s.text.strip() for s in collected)
    word_count = len(combined_text.split())
    if word_count > 9:
        return None
    return combined_text.strip()


def is_valid_heading(span, full_text_map, avg_gap_per_font):
    if not span.text.strip():
        return False, None

    extended_text = extend_heading_span(span, full_text_map, avg_gap_per_font)
    if extended_text is None:
        return False, None

    words = extended_text.strip().split()
    if len(words) > 9:
        return False, None

    text = extended_text.strip()

    # Check for pure numbers or roman numerals
    is_number = re.fullmatch(r"[0-9.,:;()\-\s]+", text) is not None
    is_roman = re.fullmatch(r"(M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))", text.upper()) is not None
    if is_number or is_roman:
        return False, None

    # Must contain at least one word with 2+ letters
    contains_word = any(re.search(r"[a-zA-Z]{2,}", word) for word in words)
    if not contains_word:
        return False, None

    # Special handling for single words - be more critical
    if len(words) == 1:
        if not is_likely_heading_word(words[0]):
            return False, None

    return True, text


def font_score(size, font_tiers):
    if abs(size - font_tiers['title']) < 0.5:
        return 5
    elif abs(size - font_tiers['H1']) < 0.5:
        return 3.5
    elif abs(size - font_tiers['H2']) < 0.5:
        return 2
    elif abs(size - font_tiers['H3']) < 0.5:
        return 1
    return 0


def position_score(span, page_height, page_width):
    score = 0
    if span.page_number == 0 and span.y < 0.2 * page_height:
        score += 2
    margin = 0.15 * page_width
    if abs(span.x + span.width / 2 - page_width / 2) < margin:
        score += 2
    return score


def style_score(span):
    score = 0
    if span.bold:
        score += 1
    if span.text.strip().isupper():
        score += 1
    return score


def compute_score(span, page_height, page_width, font_tiers):
    return (
        font_score(span.font_size, font_tiers) +
        position_score(span, page_height, page_width) +
        style_score(span)
    )


def classify_heading(score):
    if score >= 7:
        return 'H1'
    elif score >= 5:
        return 'H2'
    elif score >= 3.5:
        return 'H3'
    return None


def normalize_text_for_comparison(text):
    """Normalize text for duplicate detection"""
    # Convert to lowercase, remove extra whitespace, and common punctuation
    normalized = re.sub(r'[^\w\s]', '', text.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def extract_text_spans(doc):
    spans = []
    for page_number, page in enumerate(doc):
        blocks = page.get_text("dict")['blocks']
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if not span['text'].strip():
                        continue
                    spans.append(TextSpan(
                        text=span['text'],
                        font_size=span['size'],
                        bold="bold" in span['font'],
                        x=span['bbox'][0],
                        y=span['bbox'][1],
                        width=span['bbox'][2] - span['bbox'][0],
                        page_number=page_number
                    ))
    return spans


def extract_outline(text_spans, page_height, page_width):
    font_sizes = sorted(set(span.font_size for span in text_spans), reverse=True)
    font_tiers = {
        'title': font_sizes[0],
        'H1': font_sizes[1] if len(font_sizes) > 1 else font_sizes[0],
        'H2': font_sizes[2] if len(font_sizes) > 2 else font_sizes[-1],
        'H3': font_sizes[3] if len(font_sizes) > 3 else font_sizes[-1],
    }

    avg_gap_per_font = build_font_gap_stats(text_spans)
    spans_by_line = defaultdict(list)
    for span in text_spans:
        spans_by_line[(span.page_number, span.y)].append(span)

    outline = []
    seen_positions = set()
    seen_headings = set()  # Track seen heading texts to avoid duplicates
    
    for span in text_spans:
        key = (span.page_number, span.y, span.x)
        if key in seen_positions:
            continue
        seen_positions.add(key)
        
        valid, full_text = is_valid_heading(span, spans_by_line, avg_gap_per_font)
        if not valid:
            continue
            
        # Check for duplicate headings
        normalized_text = normalize_text_for_comparison(full_text)
        if normalized_text in seen_headings:
            continue
        
        score = compute_score(span, page_height, page_width, font_tiers)
        level = classify_heading(score)
        if level:
            seen_headings.add(normalized_text)  # Add to seen set
            outline.append({
                'level': level,
                'text': full_text,
                'page': span.page_number + 1
            })
            
    return outline


def process_pdfs():
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")

    output_dir.mkdir(parents=True, exist_ok=True)

    for pdf_file in input_dir.glob("*.pdf"):
        doc = fitz.open(pdf_file)
        page_width, page_height = doc[0].rect.width, doc[0].rect.height

        text_spans = extract_text_spans(doc)
        outline = extract_outline(text_spans, page_height, page_width)
        title = outline[0]['text'] if outline else "Untitled"

        output_data = {
            "title": title,
            "outline": outline
        }

        output_file = output_dir / f"{pdf_file.stem}.json"
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        print(f"Processed {pdf_file.name} -> {output_file.name}")


if __name__ == "__main__":
    print("Starting processing PDFs")
    process_pdfs()
    print("Completed processing PDFs")