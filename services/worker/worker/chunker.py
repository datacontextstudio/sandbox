from worker.config import settings


_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _split_text(text: str, separator: str, chunk_size: int, overlap: int) -> list[str]:
    splits = text.split(separator) if separator else list(text)
    chunks: list[str] = []
    current = ""

    for part in splits:
        candidate = (current + separator + part).lstrip(separator) if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
                # carry over overlap from the tail of current
                tail = current[-overlap:] if overlap else ""
                current = (tail + separator + part).lstrip(separator) if tail else part
            else:
                current = part

    if current:
        chunks.append(current)

    return chunks


def recursive_split(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
    separators: list[str] | None = None,
) -> list[str]:
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap if overlap is not None else settings.chunk_overlap
    separators = separators or _SEPARATORS

    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    for sep in separators:
        chunks = _split_text(text, sep, chunk_size, overlap)
        # if this separator produced meaningful splits, use them
        if len(chunks) > 1 or (len(chunks) == 1 and len(chunks[0]) <= chunk_size):
            result: list[str] = []
            for chunk in chunks:
                if len(chunk) > chunk_size:
                    # recurse with remaining separators
                    idx = separators.index(sep)
                    result.extend(recursive_split(chunk, chunk_size, overlap, separators[idx + 1:]))
                else:
                    if chunk.strip():
                        result.append(chunk)
            return result

    return [text]
