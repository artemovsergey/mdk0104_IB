#set page(
  paper: "a4",
  margin: (left: 3cm, right: 1.5cm, top: 2cm, bottom: 2cm),
  numbering: none,
)
#set text(font: "Liberation Serif", size: 14pt, lang: "ru")
#set par(justify: true, leading: 1.2em, first-line-indent: 1.25cm, spacing: 1.2em)
#set heading(numbering: none)
#show heading.where(level: 1): it => pagebreak(weak: true) + align(center)[
  #text(size: 18pt, weight: "bold")[#it.body]
]
#show heading.where(level: 2): it => block(above: 1.2em, below: 0.6em)[
  #text(size: 16pt, weight: "bold")[#it.body]
]
#show heading.where(level: 3): it => block(above: 1em, below: 0.4em)[
  #text(size: 14pt, weight: "bold", style: "italic")[#it.body]
]
#show raw.where(block: true): it => block(
  width: 100%,
  fill: luma(245),
  inset: 6pt,
  radius: 2pt,
  clip: true,
  text(font: "Liberation Mono", size: 9pt, it),
)
#show link: set text(fill: blue)
#show table: it => {
  set table(stroke: 0.5pt)
  set text(size: 9.5pt)
  set par(justify: false, leading: 0.65em, spacing: 0.65em)
  it
}
#show table.cell: it => align(left, it)
#show raw.where(block: false): set text(size: 10pt)
#let blockquote(body) = quote(block: true, body)

#let subtitle = sys.inputs.at("subtitle", default: "")

#align(center)[
  #text(size: 16pt, weight: "bold")[#sys.inputs.at("code", default: "")] \
  #text(size: 20pt, weight: "bold", hyphenate: false)[#sys.inputs.at("title", default: "")] \
  #if subtitle != "" [
    #text(size: 15pt, style: "italic")[#subtitle] \
  ]
  #v(1cm)
  #text(size: 14pt)[#sys.inputs.at("specialty", default: "")] \
  #text(size: 14pt)[#sys.inputs.at("group", default: "")] \
  #v(2cm)
  #text(size: 14pt)[#sys.inputs.at("teacher", default: "")] \
  #text(size: 14pt)[#sys.inputs.at("year", default: "")] \
  #v(1cm)
]
#pagebreak()
#set page(numbering: "1", number-align: right)

$if(toc)$
#outline(title: "Содержание", depth: 2)
#pagebreak()
$endif$

$body$
