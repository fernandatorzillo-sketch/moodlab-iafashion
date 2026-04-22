“””
recommendation_engine.py

Motor de recomendação da MoodLab.

Quando os campos de categoria/departamento/cor estão vazios no banco
(situação comum logo após a primeira sincronização do catálogo VTEX),
o engine infere essas informações pelo nome do produto.

Isso garante que as recomendações funcionem mesmo antes do catálogo
estar totalmente enriquecido com metadados.
“””

import math
from typing import Any

# ─────────────────────────────────────────────────────────────

# UTILITÁRIOS

# ─────────────────────────────────────────────────────────────

def normalize_text(value: Any) -> str:
text = str(value or “”).strip().lower()
replacements = {
“á”: “a”, “à”: “a”, “ã”: “a”, “â”: “a”,
“é”: “e”, “ê”: “e”, “í”: “i”,
“ó”: “o”, “ô”: “o”, “õ”: “o”,
“ú”: “u”, “ç”: “c”,
“/”: “ “, “-”: “ “, “_”: “ “, “|”: “ “,
}
for old, new in replacements.items():
text = text.replace(old, new)
return “ “.join(text.split())

def normalize_id(value: Any) -> str:
return str(value or “”).strip()

def as_list(value: Any) -> list[Any]:
if value is None:
return []
if isinstance(value, list):
return value
return [value]

def get_field(item: dict[str, Any], *keys: str, default: Any = “”) -> Any:
for key in keys:
if key in item and item.get(key) not in [None, “”]:
return item.get(key)
return default

# ─────────────────────────────────────────────────────────────

# EXTRATORES DE CAMPOS COM FALLBACK PELO NOME

# ─────────────────────────────────────────────────────────────

def product_name(item: dict[str, Any]) -> str:
return str(get_field(item, “nome”, “name”, “product_name”, default=“Produto”))

def product_sku(item: dict[str, Any]) -> str:
return normalize_id(get_field(item, “sku_id”, “sku”, default=””))

def product_id(item: dict[str, Any]) -> str:
return normalize_id(get_field(item, “product_id”, “id”, default=””))

def product_ref(item: dict[str, Any]) -> str:
return normalize_id(get_field(item, “ref_id”, “RefId”, default=””))

def product_link(item: dict[str, Any]) -> str:
return str(get_field(item, “link_produto”, “product_url”, “detailUrl”, “link”, default=”#”))

def product_image(item: dict[str, Any]) -> str:
direct = get_field(item, “imagem_url”, “image_url”, default=””)
if direct:
return str(direct)
images = item.get(“images”) or []
if isinstance(images, list) and images:
first = images[0]
if isinstance(first, dict):
return first.get(“ImageUrl”) or first.get(“imageUrl”) or “”
return “”

def product_price(item: dict[str, Any]) -> float:
raw = get_field(item, “price”, “preco”, default=0)
try:
return float(raw or 0)
except Exception:
return 0.0

def product_color(item: dict[str, Any]) -> str:
direct = normalize_text(get_field(item, “cor”, “color”, “cores”, default=””))
if direct:
return direct
# Tenta inferir cor pelo nome do produto
name = normalize_text(product_name(item))
cores_conhecidas = [
“preto”, “branco”, “azul”, “verde”, “vermelho”, “rosa”, “amarelo”,
“laranja”, “roxo”, “bege”, “nude”, “caramelo”, “marrom”, “cinza”,
“off white”, “coral”, “turquesa”, “estampado”, “floral”, “listrado”,
“hortela”, “areia”, “dourado”, “prata”,
]
for cor in cores_conhecidas:
if cor in name:
return cor
return “”

def product_collection(item: dict[str, Any]) -> str:
return normalize_text(get_field(item, “colecao”, “coleção”, “collection”, default=””))

def product_style(item: dict[str, Any]) -> str:
return normalize_text(get_field(item, “estilo”, “style”, default=””))

def product_occasion(item: dict[str, Any]) -> str:
return normalize_text(get_field(item, “ocasiao”, “ocasião”, “occasion”, default=””))

def product_department(item: dict[str, Any]) -> str:
“”“Extrai departamento. Se vazio, infere pelo nome e categoria do produto.”””
direct = normalize_text(get_field(item, “departamento”, “department”, default=””))
if direct:
return direct

```
# Infere pelo nome
name = normalize_text(product_name(item))
category = product_category_raw(item)  # categoria sem recursão

if any(x in name for x in ["biquini", "maio", "maiô", "sutia", "calcinha", "saida de praia", "saida praia", "canga", "pareo"]):
    return "beachwear"
if any(x in name for x in ["vestido", "saia", "blusa", "calca", "short", "camisa", "macacao", "conjunto", "kimono"]):
    return "feminino"
if any(x in name for x in ["oculos", "bolsa", "bone", "chapeu", "sandalia", "chinelo", "acessorio"]):
    return "acessorios"
if any(x in name for x in ["vaso", "vela", "almofada", "manta", "decor", "panela", "jogo americano"]):
    return "casa"
if category:
    return category

return ""
```

def product_category_raw(item: dict[str, Any]) -> str:
“”“Extrai categoria sem inferência (evita recursão).”””
return normalize_text(get_field(item, “categoria”, “category”, “product_type”, “tipo”, default=””))

def product_category(item: dict[str, Any]) -> str:
“””
Extrai categoria do produto.
Se o campo estiver vazio, infere pelo nome — essencial para
o catálogo da Água de Coco onde esses campos chegam como None.
“””
direct = product_category_raw(item)
if direct:
return direct

```
# Infere pelo nome do produto
name = normalize_text(product_name(item))

# ── Beachwear ───────────────────────────────────────────
if any(x in name for x in ["biquini", "biquíni", "sutia", "sutiã", "calcinha", "cortininha", "top de biquini"]):
    return "beachwear"
if any(x in name for x in ["maio", "maiô", "meia taca", "meia-taca", "frente unica", "frente única"]):
    return "maio"
if any(x in name for x in ["saida de praia", "saida praia", "saída praia", "canga", "pareo", "pareô", "kimono praia"]):
    return "saida_praia"

# ── Vestuário ────────────────────────────────────────────
if "vestido" in name:
    return "vestido"
if "saia" in name:
    return "saia"
if any(x in name for x in ["calca", "calça", "pantacourt", "pantalone"]):
    return "calca"
if any(x in name for x in ["short", "bermuda"]):
    return "short"
if any(x in name for x in ["blusa", "top ", " top", "cropped"]):
    return "blusa"
if any(x in name for x in ["camisa", "camiseta", "t-shirt"]):
    return "camisa"
if any(x in name for x in ["macacao", "macacão", "macacao"]):
    return "macacao"
if any(x in name for x in ["conjunto", "look"]):
    return "conjunto"
if any(x in name for x in ["kimono", "quimono"]):
    return "kimono"
if any(x in name for x in ["casaco", "cardigan", "sobretudo", "jaqueta"]):
    return "casaco"

# ── Acessórios ───────────────────────────────────────────
if any(x in name for x in ["oculos", "óculos"]):
    return "acessorio"
if any(x in name for x in ["bolsa", "bag", "clutch", "necessaire"]):
    return "acessorio"
if any(x in name for x in ["bone", "boné", "chapeu", "chapéu", "lenco", "lenço"]):
    return "acessorio"
if any(x in name for x in ["sandalia", "sandália", "chinelo", "rasteira", "tamanco", "scarpin"]):
    return "calcado"
if any(x in name for x in ["colar", "brinco", "anel", "pulseira", "bracelete", "relogio"]):
    return "joias"

# ── Casa ─────────────────────────────────────────────────
if any(x in name for x in ["vela", "almofada", "manta", "vaso", "jarra", "panela",
                             "decor", "jogo americano", "toalha", "porta", "cesta",
                             "mini vaso", "sanfonado", "difusor"]):
    return "casa"

return "outros"
```

# ─────────────────────────────────────────────────────────────

# PERFIL DO CLOSET

# ─────────────────────────────────────────────────────────────

def infer_profile(closet_products: list[dict[str, Any]]) -> dict[str, Any]:
“”“Analisa o closet e extrai o perfil dominante da cliente.”””

```
def top_value(values: list[str]) -> str:
    clean = [v for v in values if v]
    if not clean:
        return ""
    return max(set(clean), key=clean.count)

categories   = [product_category(p) for p in closet_products]
departments  = [product_department(p) for p in closet_products]
colors       = [product_color(p) for p in closet_products]
collections  = [product_collection(p) for p in closet_products]
styles       = [product_style(p) for p in closet_products]
occasions    = [product_occasion(p) for p in closet_products]

return {
    "dominant_category":    top_value(categories),
    "dominant_department":  top_value(departments),
    "dominant_color":       top_value(colors),
    "dominant_collection":  top_value(collections),
    "dominant_style":       top_value(styles),
    "dominant_occasion":    top_value(occasions),
    "owned_categories":     sorted({c for c in categories if c}),
    "owned_departments":    sorted({d for d in departments if d}),
    "owned_collections":    sorted({c for c in collections if c}),
}
```

def get_owned_sets(closet_products: list[dict[str, Any]]) -> dict[str, set[str]]:
return {
“sku_ids”:    {product_sku(p) for p in closet_products if product_sku(p)},
“product_ids”:{product_id(p) for p in closet_products if product_id(p)},
“ref_ids”:    {product_ref(p) for p in closet_products if product_ref(p)},
“names”:      {normalize_text(product_name(p)) for p in closet_products if product_name(p)},
}

def is_already_owned(candidate: dict[str, Any], owned_sets: dict[str, set[str]]) -> bool:
if product_sku(candidate) and product_sku(candidate) in owned_sets[“sku_ids”]:
return True
if product_id(candidate) and product_id(candidate) in owned_sets[“product_ids”]:
return True
if product_ref(candidate) and product_ref(candidate) in owned_sets[“ref_ids”]:
return True
if normalize_text(product_name(candidate)) in owned_sets[“names”]:
return True
return False

# ─────────────────────────────────────────────────────────────

# REGRAS DE LOOK (baseadas nas respostas do quiz)

# ─────────────────────────────────────────────────────────────

def look_rules_for_answers(answers: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
# Aceita tanto português quanto inglês nas chaves
ocasiao  = normalize_text(answers.get(“ocasiao”) or answers.get(“occasion”) or “”)
objetivo = normalize_text(answers.get(“objetivo”) or answers.get(“goal”) or “”)
estilo   = normalize_text(answers.get(“estilo”)   or answers.get(“style”)  or “”)

```
dominant_category   = profile.get("dominant_category", "")
owned_categories    = set(profile.get("owned_categories", []))

allowed_categories: set[str] = set()
blocked_categories: set[str] = {"casa"}

is_beach_profile = dominant_category in {"beachwear", "maio", "saida_praia"} \
                   or bool(owned_categories & {"beachwear", "maio", "saida_praia"})

if is_beach_profile:
    allowed_categories.update({"beachwear", "maio", "saida_praia", "saia", "acessorio", "calcado", "kimono"})

    if objetivo in {"completar_look", "completar look", "cross_sell"}:
        allowed_categories.update({"saida_praia", "saia", "acessorio", "calcado", "kimono"})
        blocked_categories.add("vestido")

    if objetivo in {"similares", "up_sell"}:
        allowed_categories.update({"beachwear", "maio"})

else:
    # Perfil vestuário geral
    allowed_categories.update({
        "vestido", "saia", "blusa", "calca", "short", "camisa",
        "acessorio", "calcado", "joias", "outros",
        dominant_category,
    })

# Ocasião praia libera tudo de praia mesmo sem perfil dominante
if ocasiao in {"praia", "praia resort", "resort"}:
    allowed_categories.update({"beachwear", "maio", "saida_praia", "saia", "acessorio", "calcado"})

return {
    "ocasiao":            ocasiao,
    "objetivo":           objetivo,
    "estilo":             estilo,
    "allowed_categories": {x for x in allowed_categories if x},
    "blocked_categories": blocked_categories,
}
```

# ─────────────────────────────────────────────────────────────

# FILTRO DE CANDIDATOS

# ─────────────────────────────────────────────────────────────

def candidate_blocked(
candidate: dict[str, Any],
profile: dict[str, Any],
rules: dict[str, Any],
) -> bool:
category   = product_category(candidate)
department = product_department(candidate)

```
# Bloqueia categorias explicitamente bloqueadas
if category in rules["blocked_categories"]:
    return True

# Bloqueia itens de casa (não é moda)
if department == "casa" or category == "casa":
    return True

# Se há categorias permitidas definidas, filtra por elas
allowed = rules["allowed_categories"]
if allowed and category not in allowed:
    return True

return False
```

# ─────────────────────────────────────────────────────────────

# PONTUAÇÃO DE CANDIDATOS

# ─────────────────────────────────────────────────────────────

def score_candidate(
candidate: dict[str, Any],
closet_products: list[dict[str, Any]],
profile: dict[str, Any],
rules: dict[str, Any],
) -> tuple[float, list[str]]:
score = 0.0
reasons: list[str] = []

```
category   = product_category(candidate)
department = product_department(candidate)
color      = product_color(candidate)
collection = product_collection(candidate)
style      = product_style(candidate)
occasion   = product_occasion(candidate)
price      = product_price(candidate)

dominant_category  = profile.get("dominant_category", "")
dominant_dept      = profile.get("dominant_department", "")
dominant_color     = profile.get("dominant_color", "")
dominant_collection= profile.get("dominant_collection", "")
dominant_style     = profile.get("dominant_style", "")
owned_categories   = set(profile.get("owned_categories", []))

objetivo = rules["objetivo"]
ocasiao  = rules["ocasiao"]
estilo   = rules["estilo"]

# ── Afinidade com o closet ───────────────────────────────
if category and category == dominant_category:
    score += 35
    reasons.append("Parecido com o que ela já compra")

if department and dominant_dept and department == dominant_dept:
    score += 20
    reasons.append("Mesmo departamento das compras anteriores")

if color and dominant_color and color == dominant_color:
    score += 10
    reasons.append("Cor alinhada ao closet")

if collection and dominant_collection and collection == dominant_collection:
    score += 10
    reasons.append("Coleção próxima do histórico")

if style and dominant_style and style == dominant_style:
    score += 10
    reasons.append("Estilo compatível")

if occasion and ocasiao and occasion == ocasiao:
    score += 15
    reasons.append("Combina com a ocasião escolhida")

# ── Lógica de praia (perfil dominante da Água de Coco) ───
is_beach_profile = dominant_category in {"beachwear", "maio", "saida_praia"} \
                   or bool(owned_categories & {"beachwear", "maio", "saida_praia"})

if is_beach_profile:
    if category in {"saida_praia", "saia", "acessorio", "calcado", "kimono"}:
        score += 30
        reasons.append("Complementa o look de praia")

    if category in {"beachwear", "maio"} and objetivo in {"similares", "up_sell"}:
        score += 25
        reasons.append("Similar ao que ela já ama")

    # Penaliza vestido de festa para perfil praia
    if category == "vestido" and ocasiao not in {"festa", "evento", "jantar"}:
        score -= 50

# ── Objetivo do quiz ─────────────────────────────────────
if objetivo in {"completar_look", "completar look", "cross_sell"}:
    if category in {"saida_praia", "saia", "acessorio", "calcado", "kimono", "joias"}:
        score += 25
        reasons.append("Ajuda a completar o look")

elif objetivo in {"up_sell"}:
    if category not in owned_categories:
        score += 20
        reasons.append("Expande o closet com novidade")

elif objetivo in {"novidades"}:
    score += 8
    reasons.append("Novidade para o closet")

# ── Estilo do quiz ───────────────────────────────────────
if estilo and style and style == estilo:
    score += 15
    reasons.append("Combina com o estilo escolhido")

# ── Faixa de preço similar ───────────────────────────────
if price > 0:
    avg = average_price(closet_products)
    if avg > 0:
        diff_ratio = abs(price - avg) / max(avg, 1)
        score += max(0, 10 - (diff_ratio * 8))

# ── Score mínimo para aparecer ───────────────────────────
# Garante pelo menos score 5 para produtos do mesmo departamento
# (resolve o caso de campos None com inferência pelo nome)
if score == 0 and department and dominant_dept and department == dominant_dept:
    score = 5
    reasons.append("Mesmo universo de compra")

reasons = dedupe_preserve_order(reasons)
return score, reasons
```

def average_price(products: list[dict[str, Any]]) -> float:
prices = [product_price(p) for p in products if product_price(p) > 0]
if not prices:
return 0.0
return sum(prices) / len(prices)

def dedupe_preserve_order(items: list[str]) -> list[str]:
seen = set()
result = []
for item in items:
if item not in seen:
seen.add(item)
result.append(item)
return result

# ─────────────────────────────────────────────────────────────

# FUNÇÃO PRINCIPAL

# ─────────────────────────────────────────────────────────────

def build_recommendations(
closet_products: list[dict[str, Any]],
catalog: list[dict[str, Any]],
answers: dict[str, Any],
style_preferences: dict | None = None,
limit: int = 8,
) -> dict[str, Any]:
“””
Gera recomendações personalizadas para uma cliente.

```
Funciona mesmo quando:
- Os campos categoria/departamento/cor estão None no banco
  (infere pelo nome do produto)
- O cliente ainda não respondeu o quiz (answers={})
- É a primeira compra (closet com 1 item)
"""
profile    = infer_profile(closet_products)
owned_sets = get_owned_sets(closet_products)
rules      = look_rules_for_answers(answers, profile)

ranked: list[dict[str, Any]] = []

for candidate in catalog:
    if is_already_owned(candidate, owned_sets):
        continue

    if candidate_blocked(candidate, profile, rules):
        continue

    score, reasons = score_candidate(candidate, closet_products, profile, rules)

    if score <= 0:
        continue

    ranked.append({
        "produto_id":   product_id(candidate),
        "sku_id":       product_sku(candidate),
        "ref_id":       product_ref(candidate),
        "nome":         product_name(candidate),
        "name":         product_name(candidate),
        "imagem_url":   product_image(candidate),
        "image_url":    product_image(candidate),
        "categoria":    product_category(candidate),
        "category":     product_category(candidate),
        "departamento": product_department(candidate),
        "department":   product_department(candidate),
        "cor":          product_color(candidate),
        "color":        product_color(candidate),
        "colecao":      product_collection(candidate),
        "estilo":       product_style(candidate),
        "price":        product_price(candidate),
        "link_produto": product_link(candidate),
        "product_url":  product_link(candidate),
        "motivo":       reasons[0] if reasons else "Selecionado para você",
        "reason":       reasons[0] if reasons else "Selecionado para você",
        "score":        round(score, 2),
        "reasons":      reasons,
    })

ranked.sort(key=lambda x: x["score"], reverse=True)

return {
    "profile": profile,
    "rules": {
        "ocasiao":            rules["ocasiao"],
        "objetivo":           rules["objetivo"],
        "estilo":             rules["estilo"],
        "allowed_categories": sorted(rules["allowed_categories"]),
        "blocked_categories": sorted(rules["blocked_categories"]),
    },
    "recommendations": ranked[:limit],
    "human_message": _build_message(profile, ranked[:limit], answers),
    "meta": {
        "catalog_size":    len(catalog),
        "closet_size":     len(closet_products),
        "ranked_count":    len(ranked),
        "returned_count":  min(len(ranked), limit),
    },
}
```

def _build_message(profile: dict, recs: list, answers: dict) -> str:
“”“Gera mensagem humanizada para o cliente.”””
ocasiao  = answers.get(“ocasiao”) or answers.get(“occasion”) or “”
objetivo = answers.get(“objetivo”) or answers.get(“goal”) or “”

```
if not recs:
    return "Em breve teremos sugestões personalizadas para você!"

dominant = profile.get("dominant_category", "")

if dominant in {"beachwear", "maio", "saida_praia"}:
    base = "Separei peças perfeitas para completar seus looks de praia"
elif ocasiao:
    base = f"Separei peças pensando em {ocasiao}"
else:
    base = "Separei peças especialmente para o seu estilo"

if objetivo in {"completar_look", "completar look", "cross_sell"}:
    complemento = ", para completar seus looks com o que você já tem."
elif objetivo in {"novidades"}:
    complemento = ", novidades da coleção que combinam com o seu closet."
else:
    complemento = ", escolhidas com base no seu histórico de compras."

return base + complemento
```