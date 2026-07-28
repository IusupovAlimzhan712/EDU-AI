/**
 * SPM Sejarah key terms to highlight in AI tutor responses.
 * Terms are matched case-insensitively and wrapped in **bold** markdown.
 * Multi-word terms are listed first so they are matched before their components.
 */
const KEY_TERMS: string[] = [
  // Treaties & agreements
  'Perjanjian Pangkor',
  'Perjanjian Bangkok',
  'Perjanjian Persekutuan',
  'Perjanjian Britain-Belanda',
  'Sistem Residen',
  'Sistem Penasihat',

  // Policies & plans
  'Dasar Ekonomi Baru',
  'Dasar Pembangunan Nasional',
  'Dasar Pandang ke Timur',
  'Dasar Penswastaan',
  'Wawasan 2020',
  'Rancangan Malaysia',
  'Rukun Negara',

  // Organizations & parties
  'Barisan Nasional',
  'Perikatan',
  'Pakatan Harapan',
  'UMNO',
  'MCA',
  'MIC',
  'FELDA',
  'Parti Komunis Malaya',
  'PKM',
  'Kongres India Se-Malaya',
  'Kesatuan Melayu Singapura',

  // Key documents
  'Perlembagaan Persekutuan',
  'Perlembagaan Malaysia',
  'Kontrak Sosial',
  'Artikel 153',

  // Historical events
  'Peristiwa 13 Mei',
  'Darurat',
  'Perang Dunia Pertama',
  'Perang Dunia Kedua',
  'Pendudukan Jepun',
  'Zaman Pendudukan Jepun',
  'Kemerdekaan Malaya',
  'Pembentukan Malaysia',

  // Prominent figures
  'Tunku Abdul Rahman',
  'Tun Abdul Razak',
  'Tun Hussein Onn',
  'Tun Mahathir Mohamad',
  'Tun Abdullah Ahmad Badawi',
  'Onn Jaafar',
  'Ibrahim Yaakob',
  'Parameswara',
  'Hang Tuah',
  'Hang Jebat',
  'Raja Ali Haji',
  'Dato Maharajalela',
  'Tok Janggut',
  'Mat Salleh',

  // Historical kingdoms & civilisations
  'Kesultanan Melayu Melaka',
  'Kerajaan Melayu Melaka',
  'Majapahit',
  'Srivijaya',
  'Sriwijaya',
  'Kerajaan Kedah Tua',

  // Concepts
  'Nasionalisme',
  'Federalisme',
  'Demokrasi Berparlimen',
  'Raja Berperlembagaan',
  'Hak Keistimewaan Melayu',
  'Bahasa Kebangsaan',
  'Islam Hadhari',
];

// Pre-compile: sort longest first so multi-word phrases match before single words.
// Build one regex per term; cache them here.
const TERM_PATTERNS: Array<{ re: RegExp; term: string }> = KEY_TERMS
  .sort((a, b) => b.length - a.length)
  .map((term) => ({
    term,
    re: new RegExp(
      // Use Unicode word-boundary equivalent: assert non-letter before/after
      `(?<![A-Za-zÀ-öø-ÿ])(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})(?![A-Za-zÀ-öø-ÿ])`,
      'gi',
    ),
  }));

/**
 * Wrap recognised SPM Sejarah key terms in **bold** markdown.
 *
 * Safe to call on streamed text or final responses.
 * - Skips content already inside `**...**` to avoid double-wrapping.
 * - Skips content inside code spans (`...`) and fenced code blocks.
 * - Does not modify user messages — only call on assistant content.
 */
export function highlightKeyTerms(text: string): string {
  if (!text) return text;

  // Split on already-bold segments (**...**) and code spans (`...`).
  // Even indices → plain text to process; odd indices → leave untouched.
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);

  return parts
    .map((part, i) => {
      // Odd parts are already styled — leave them alone.
      if (i % 2 !== 0) return part;
      // Skip fenced code blocks (lines starting with ```)
      if (part.trimStart().startsWith('```')) return part;

      let result = part;
      for (const { re, term: _term } of TERM_PATTERNS) {
        // $1 preserves the original casing of the matched text
        result = result.replace(re, '**$1**');
        // Reset lastIndex in case the regex is stateful (it's not with 'gi' + new string, but be safe)
        re.lastIndex = 0;
      }
      return result;
    })
    .join('');
}
