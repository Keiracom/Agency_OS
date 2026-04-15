"""
Canonical domain blocklist for discovery pipeline.
Categorised by reason for auditability.
Directives: #267 (original), #328 Stage 1 (expansion)

TRADEOFF (ratified by CEO, #328 Stage 1):
  Strict AU-only enforcement. Domains must have a commercial AU TLD
  (.com.au, .net.au, .id.au, .asn.au, .sydney, .melbourne, .perth, .brisbane).
  This rejects legitimate AU businesses using .com, .co, .io, .ai TLDs
  (~5% false negative rate). Accepted tradeoff: cleaner discovery inputs
  outweigh the loss. A future directive can add ABN-validated non-.au
  recovery as a secondary path.
"""
from __future__ import annotations

import re

# ── GOVERNMENT TLDs (all countries) ──────────────────────────────────────────
# Regex: any domain ending in .gov, .govt, .go.XX, .gov.XX, .gouv.XX, .gob.XX
_GOVERNMENT_RE = re.compile(
    r'\.(gov|govt|government|gob|gouv)(\.[a-z]{2,3})?$',
    re.IGNORECASE,
)

# ── AU TLD WHITELIST ─────────────────────────────────────────────────────────
# A domain MUST match one of these to be considered AU.
# .org.au and .edu.au are excluded — industry bodies and institutions, not SMBs.
# Anything else is rejected regardless of DFS location tag.
AU_TLD_WHITELIST = frozenset({
    ".com.au", ".net.au", ".id.au", ".asn.au",
    ".sydney", ".melbourne", ".perth", ".brisbane",
})

# ── SOCIAL PLATFORMS ─────────────────────────────────────────────────────────
SOCIAL_PLATFORMS = frozenset({
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "tiktok.com", "pinterest.com", "snapchat.com", "reddit.com",
    "youtube.com", "linkedin.com", "threads.net", "whatsapp.com",
})

# ── SEARCH / TECH GIANTS ────────────────────────────────────────────────────
TECH_GIANTS = frozenset({
    "google.com", "google.com.au", "bing.com", "yahoo.com",
    "apple.com", "microsoft.com", "amazon.com", "amazon.com.au",
})

# ── WEBSITE BUILDERS / PLATFORMS ─────────────────────────────────────────────
WEBSITE_BUILDERS = frozenset({
    "wordpress.com", "wix.com", "squarespace.com", "shopify.com",
    "webflow.com", "weebly.com", "blogger.com",
})

# ── HOSTING / INFRA / DEV ───────────────────────────────────────────────────
HOSTING_INFRA = frozenset({
    "godaddy.com", "cloudflare.com", "github.com", "gitlab.com",
    "stackoverflow.com", "medium.com", "notion.so", "calendly.com",
    "stripe.com", "dropbox.com", "slack.com", "zoom.us",
    "forms.office.com", "docs.google.com", "drive.google.com",
})

# ── AU GOVERNMENT (specific) ────────────────────────────────────────────────
AU_GOVERNMENT = frozenset({
    "gov.au", "nsw.gov.au", "vic.gov.au", "qld.gov.au",
    "sa.gov.au", "wa.gov.au", "tas.gov.au", "act.gov.au",
    "nt.gov.au", "health.gov.au", "ato.gov.au", "abn.business.gov.au",
    "humanservices.gov.au", "centrelink.gov.au",
})

# ── AU MEDIA / LIFESTYLE ────────────────────────────────────────────────────
AU_MEDIA = frozenset({
    "homestolove.com.au", "realestate.com.au", "domain.com.au",
    "news.com.au", "abc.net.au", "sbs.com.au", "smh.com.au",
    "theage.com.au", "9news.com.au", "7news.com.au",
    "dailytelegraph.com.au", "couriermail.com.au",
    "heraldsun.com.au", "perthnow.com.au", "adelaidenow.com.au",
    "brisbanetimes.com.au", "canberratimes.com.au",
    "theaustralian.com.au", "afr.com", "theguardian.com",
    "bhg.com", "architecturaldigest.com", "dwell.com",
    "houzz.com", "houzz.com.au",
})

# ── AGGREGATORS / DIRECTORIES ────────────────────────────────────────────────
AGGREGATORS = frozenset({
    # Healthcare
    "whatclinic.com", "healthengine.com.au", "hotdoc.com.au",
    # General
    "yelp.com", "yelp.com.au", "hipages.com.au", "oneflare.com.au",
    "expertise.com", "trustpilot.com", "localsearch.com.au",
    "truelocal.com.au", "yellowpages.com.au", "whitecoat.com.au",
    "servicecentral.com.au", "wordofmouth.com.au", "startlocal.com.au",
    "productreview.com.au",
    # Legal
    "lawsociety.com.au", "findlaw.com.au", "legalvision.com.au",
    "lawpath.com.au", "legalmatch.com.au", "lawyerslist.com.au",
    # Construction
    "masterbuilders.com.au", "buildsearch.com.au",
    "architectslist.com.au",
    # Industry bodies / bar associations
    "ada.org.au", "ada.org", "finder.orthodonticsaustralia.org.au",
    "hia.com.au", "aibs.com.au", "lawcouncil.asn.au",
    "qls.com.au", "vicbar.com.au", "austbar.asn.au",
    # Legal / industry media
    "lsj.com.au", "lawyersweekly.com.au", "lawfoundation.net.au",
})

# ── CONSTRUCTION RETAILERS / DISTRIBUTORS ────────────────────────────────────
CONSTRUCTION_RETAILERS = frozenset({
    "bunnings.com.au", "trade.bunnings.com.au",
    "beaumont-tiles.com.au", "nationaltiles.com.au",
    "totaltools.com.au", "sydneytools.com.au", "tradetools.com",
    "blackwoods.com.au", "rs-online.com", "au.rs-online.com",
    "bostik.com.au", "selleys.com.au",
    "dulux.com.au", "taubmans.com.au", "haymes.com.au", "wattyl.com.au",
    "mitre10.com.au", "homehardware.com.au",
    "reece.com.au", "tradelink.com.au", "samios.net.au",
    "plumbingsales.com.au", "csr.com.au", "boral.com.au",
    "jameshardie.com.au", "bluescope.com.au",
})

# ── BRANDS / MULTINATIONALS ─────────────────────────────────────────────────
BRANDS = frozenset({
    "invisalign.com.au", "colgate.com.au", "oralb.com.au",
    "3m.com.au", "henryschein.com.au",
})

# ── INSURANCE / HEALTH FUNDS ────────────────────────────────────────────────
HEALTH_FUNDS = frozenset({
    "bupa.com.au", "medibank.com.au", "hcf.com.au", "nib.com.au",
    "healthpartners.com.au", "ahm.com.au", "help.ahm.com.au", "cbhs.com.au",
})

# ── FRANCHISE / CHAIN PARENTS ────────────────────────────────────────────────
# Dental chains
DENTAL_CHAINS = frozenset({
    "1300smiles.com.au", "primarydental.com.au", "maven.dental",
    "mavendental.com.au", "pacificsmiles.com.au", "smilepath.com.au",
    "stjohnhealth.com.au", "dentalcorp.com.au", "nationaldentalcare.com.au",
    "bupadental.com.au", "nibdental.com.au", "smileclub.com.au",
    "dentalone.com.au", "marchorthodontics.com.au", "totalortho.com.au",
    "rsdentalgroup.com.au", "smilesolutions.com.au", "mcdental.com.au",
    "odontologie.com.au", "smileteam.com.au",
    "dentalboutique.com.au", "allon4.com.au", "myimplantdentist.com.au",
})

# Construction chains
CONSTRUCTION_CHAINS = frozenset({
    "metricon.com.au", "henleyhomes.com.au", "porterdavis.com.au",
    "mainstreetbuilders.com.au", "simonds.com.au", "burbank.com.au",
    "carlislegroup.com.au", "ablgroup.com.au", "lendlease.com.au",
    "hutchinsonbuilders.com.au", "multiplex.global", "probuild.com.au",
    "watpac.com.au", "mirvac.com.au", "stockland.com.au",
    "mcdonaldjoneshomes.com.au",
})

# Legal chains
LEGAL_CHAINS = frozenset({
    "slatergordon.com.au", "mauriceblackburn.com.au", "shineapp.com.au",
    "shinelawyers.com.au", "shine.com.au", "gordonlegal.com.au", "holdingredlich.com",
    "hallandwilcox.com.au", "minterellison.com", "allens.com.au",
    "claytonutz.com", "corrs.com.au", "herbertsmithfreehills.com",
    "ashurst.com", "kingwood.com.au", "gilberttobin.com",
    "nortonrosefulbright.com",
    "hwlebsworth.com.au", "lawpartners.com.au", "www.queenslandjudgments.com.au",
})

# Auto franchise chains
AUTO_CHAINS = frozenset({
    "ultratune.com.au", "midas.com.au", "bobjane.com.au",
    "strathfieldcardepot.com.au", "kwikfit.com.au",
    "jarcar.com.au", "repco.com.au", "supercheapauto.com.au",
    "autobarn.com.au",
})

# Non-AU dental tourism / foreign clinics
FOREIGN_CLINICS = frozenset({
    "bangkokdentalcenter.com", "adalyadentalclinic.com",
})

# Fitness chains
FITNESS_CHAINS = frozenset({
    "fernwoodfitness.com.au", "anytimefitness.com.au", "f45training.com.au",
    "snapfitness.com.au", "fitnessfirst.com.au", "planetfitness.com.au",
    "planetfitnessaustralia.com.au", "orangetheory.com.au", "goodlifehealthclubs.com.au",
    "plus.com.au", "vaboretum.com.au", "goldsgym.com.au",
    "worldgym.com.au", "worldgymaustralia.com.au", "24hourfitness.com.au",
    "curves.com.au", "jettsfitness.com.au", "zap.fitness", "clubfitness.com.au",
    "dynamofitness.com.au", "gymdirect.com.au", "www.genesisfitness.com.au",
    "www.virginactive.com.au",
})

# Food/restaurant chains
FOOD_CHAINS = frozenset({
    "pizzahut.com.au", "dominos.com.au", "mcdonalds.com.au", "kfc.com.au",
    "hungryjacks.com.au", "guzmanygomez.com.au", "subway.com.au",
    "redrooster.com.au", "oporto.com.au", "nandos.com.au",
    "zambrero.com.au", "madmex.com.au", "grilld.com.au",
    "bettys.com.au", "sanschurro.com.au", "theboathousergroup.com.au",
    "stellarestaurants.com.au", "merivale.com.au", "nrg.com.au",
})

# Media companies / publishing / directories
MEDIA_COMPANIES = frozenset({
    "news.com.au", "abc.net.au", "sbs.com.au",
    "gourmettraveller.com.au", "delicious.com.au", "broadsheet.com.au",
    "timeout.com", "urbanlist.com", "concreteplayground.com",
    "bestrestaurants.com.au", "goodfood.com.au", "theguardian.com",
    "stylemagazines.com.au", "frankie.com.au", "monocle.com",
    "yellowpages.com.au", "truelocal.com.au", "localsearch.com.au",
    "whitecoat.com.au", "hotdoc.com.au", "healthengine.com.au",
    "quandoo.com.au", "dimmi.com.au", "opentable.com.au",
})

# ── ACCOUNTING CHAINS ────────────────────────────────────────────────────────
ACCOUNTING_CHAINS = frozenset({
    "pwc.com.au", "www.pwc.com.au", "bdo.com.au", "www.bdo.com.au",
    "cpaaustralia.com.au", "www.cpaaustralia.com.au",
    "grantthornton.com.au", "www.grantthornton.com.au",
    "bentleys.com.au", "www.bentleys.com.au",
    "taxstore.com.au", "mlc.com.au", "www.mlc.com.au",
    "www.smart.com.au", "oneclicklife.com.au",
    "www.maxxia.com.au", "iorder.com.au",
    "deloitte.com.au", "kpmg.com.au", "ey.com",
})

# ── GOVERNMENT HEALTH ─────────────────────────────────────────────────────────
GOVERNMENT_HEALTH = frozenset({
    "www.ipchealth.com.au", "dental.mthc.com.au",
    "www.elizabethmedicalcentre.com.au",
    "www.sawater.com.au",
})

# ── INDUSTRIAL WHOLESALE ─────────────────────────────────────────────────────
INDUSTRIAL_WHOLESALE = frozenset({
    "www.holmanindustries.com.au", "store.brita.com.au",
    "www.megt.com.au", "www.actrol.com.au",
    "www.completehomefiltration.com.au",
})

# ── COMBINED SET (for exact/subdomain match) ─────────────────────────────────
BLOCKED_DOMAINS: frozenset[str] = (
    SOCIAL_PLATFORMS | TECH_GIANTS | WEBSITE_BUILDERS | HOSTING_INFRA |
    AU_GOVERNMENT | AU_MEDIA | AGGREGATORS | CONSTRUCTION_RETAILERS |
    BRANDS | HEALTH_FUNDS | DENTAL_CHAINS | CONSTRUCTION_CHAINS |
    LEGAL_CHAINS | AUTO_CHAINS | FOREIGN_CLINICS | FITNESS_CHAINS |
    FOOD_CHAINS | MEDIA_COMPANIES | ACCOUNTING_CHAINS | GOVERNMENT_HEALTH |
    INDUSTRIAL_WHOLESALE
)


def is_au_domain(domain: str) -> bool:
    """Return True if domain has an AU TLD (commercial SMB TLDs only).

    .org.au and .edu.au are excluded — industry bodies and institutions.
    """
    d = domain.lower().strip()
    return any(d.endswith(suffix) for suffix in AU_TLD_WHITELIST)


def is_blocked(domain: str | None) -> bool:
    """Return True if domain should be excluded from discovery.

    Checks (in order — cheapest/broadest first):
    1. Empty / None
    2. AU enforcement — must have commercial AU TLD (cheapest regex, kills largest chunk)
    3. Government TLD regex (all countries — catches .gov.au that passed AU check)
    4. Exact match in BLOCKED_DOMAINS (retailer/chain/media/aggregator)
    5. Subdomain of a blocked domain
    """
    if not domain:
        return True
    d = domain.lower().strip()
    if not d:
        return True

    # Pass 1: AU enforcement — must have commercial AU TLD (cheapest, biggest kill)
    if not is_au_domain(d):
        return True

    # Pass 2: Government TLD (catches .gov.au that passed AU whitelist)
    if _GOVERNMENT_RE.search(d):
        return True

    # Exact match (with and without www.)
    d_nowww = d.removeprefix("www.")
    if d_nowww in BLOCKED_DOMAINS or d in BLOCKED_DOMAINS:
        return True

    # Subdomain of blocked domain
    return any(d.endswith("." + blocked) for blocked in BLOCKED_DOMAINS)
