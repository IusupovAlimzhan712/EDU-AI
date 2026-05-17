"""
BM synonym expansion for historical/political BM vocabulary.

Used during retrieval to expand query keywords so that questions using
synonym A still match documents that use synonym B.

Example: "raja" → also search for "sultan", "pemimpin", "pemerintah".
"""
from typing import List

# Each tuple is a synonym group — if any member appears in the query,
# all members are added to the expanded keyword list.
SYNONYM_GROUPS: List[tuple] = [
    # Rulers / leadership
    ('raja', 'sultan', 'pemimpin', 'pemerintah', 'penguasa', 'ketua'),
    ('pengasas', 'pengasas', 'pencipta', 'pembina', 'penubuh'),
    ('kerajaan', 'pemerintahan', 'empayar', 'kesultanan'),
    ('rakyat', 'penduduk', 'warganegara', 'bangsa', 'masyarakat'),

    # Colonial / foreign powers
    ('penjajah', 'penjajahan', 'kolonial', 'imperialis'),
    ('british', 'inggeris', 'koloni'),
    ('portugis', 'sepanyol', 'belanda', 'barat'),
    ('jepun', 'jepang'),

    # Historical events
    ('perang', 'pertempuran', 'konflik', 'serangan', 'pencerobohan'),
    ('kemerdekaan', 'kebebasan', 'merdeka', 'kedaulatan'),
    ('perjanjian', 'persetiaan', 'persetujuan', 'perjanjian damai'),
    ('pemberontakan', 'penentangan', 'kebangkitan', 'revolusi'),
    ('pendudukan', 'penaklukan', 'penguasaan'),

    # Economic / trade
    ('perdagangan', 'perniagaan', 'dagang', 'ekonomi'),
    ('pelabuhan', 'bandar', 'pusat perdagangan'),
    ('cukai', 'hasil', 'bayaran', 'pungutan'),

    # Social / cultural
    ('agama', 'kepercayaan', 'ugama'),
    ('islam', 'muslim', 'melayu'),
    ('pendidikan', 'pelajaran', 'ilmu', 'sekolah'),
    ('budaya', 'adat', 'tradisi', 'warisan'),

    # Government / political structure
    ('perlembagaan', 'undang-undang', 'kanun', 'akta', 'dasar'),
    ('pilihan raya', 'pilihan', 'demokrasi', 'mengundi', 'parlimen'),
    ('keselamatan', 'pertahanan', 'tentera', 'polis'),
    ('pembangunan', 'kemajuan', 'pertumbuhan', 'perindustrian'),
]

# Build a flat lookup: term → set of synonyms (excluding itself)
_SYNONYM_MAP: dict = {}
for group in SYNONYM_GROUPS:
    for term in group:
        others = set(group) - {term}
        if term not in _SYNONYM_MAP:
            _SYNONYM_MAP[term] = set()
        _SYNONYM_MAP[term].update(others)


def expand_keywords(keywords: List[str]) -> List[str]:
    """Return keywords + any synonyms found in the synonym map.

    Preserves original order; appended synonyms do not duplicate existing terms.
    """
    seen = set(keywords)
    expanded = list(keywords)
    for kw in keywords:
        for syn in _SYNONYM_MAP.get(kw, []):
            if syn not in seen:
                seen.add(syn)
                expanded.append(syn)
    return expanded
