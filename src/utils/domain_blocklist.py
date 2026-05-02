"""
Canonical domain blocklist for discovery pipeline.
Categorised by reason for auditability.
Directives: #267 (original), #328 Stage 1 (expansion), D2.1A (1500+ expansion)

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
    r"\.(gov|govt|government|gob|gouv)(\.[a-z]{2,3})?$",
    re.IGNORECASE,
)

# ── AU TLD WHITELIST ─────────────────────────────────────────────────────────
# A domain MUST match one of these to be considered AU.
# .org.au and .edu.au are excluded — industry bodies and institutions, not SMBs.
# Anything else is rejected regardless of DFS location tag.
AU_TLD_WHITELIST = frozenset(
    {
        ".com.au",
        ".net.au",
        ".id.au",
        ".asn.au",
        ".sydney",
        ".melbourne",
        ".perth",
        ".brisbane",
    }
)

# ── SOCIAL PLATFORMS ─────────────────────────────────────────────────────────
SOCIAL_PLATFORMS = frozenset(
    {
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "tiktok.com",
        "pinterest.com",
        "snapchat.com",
        "reddit.com",
        "youtube.com",
        "linkedin.com",
        "threads.net",
        "whatsapp.com",
    }
)

# ── SEARCH / TECH GIANTS ────────────────────────────────────────────────────
TECH_GIANTS = frozenset(
    {
        "google.com",
        "google.com.au",
        "bing.com",
        "yahoo.com",
        "apple.com",
        "microsoft.com",
        "amazon.com",
        "amazon.com.au",
    }
)

# ── WEBSITE BUILDERS / PLATFORMS ─────────────────────────────────────────────
WEBSITE_BUILDERS = frozenset(
    {
        "wordpress.com",
        "wix.com",
        "squarespace.com",
        "shopify.com",
        "webflow.com",
        "weebly.com",
        "blogger.com",
    }
)

# ── HOSTING / INFRA / DEV ───────────────────────────────────────────────────
HOSTING_INFRA = frozenset(
    {
        "godaddy.com",
        "cloudflare.com",
        "github.com",
        "gitlab.com",
        "stackoverflow.com",
        "medium.com",
        "notion.so",
        "calendly.com",
        "stripe.com",
        "dropbox.com",
        "slack.com",
        "zoom.us",
        "forms.office.com",
        "docs.google.com",
        "drive.google.com",
    }
)

# ── AU GOVERNMENT (specific) ────────────────────────────────────────────────
AU_GOVERNMENT = frozenset(
    {
        # Catch-all TLD
        "gov.au",
        # State portals
        "nsw.gov.au",
        "vic.gov.au",
        "qld.gov.au",
        "sa.gov.au",
        "wa.gov.au",
        "tas.gov.au",
        "act.gov.au",
        "nt.gov.au",
        # Federal departments
        "health.gov.au",
        "ato.gov.au",
        "abn.business.gov.au",
        "humanservices.gov.au",
        "centrelink.gov.au",
        "defence.gov.au",
        "education.gov.au",
        "agriculture.gov.au",
        "homeaffairs.gov.au",
        "treasury.gov.au",
        "ag.gov.au",
        "industry.gov.au",
        "infrastructure.gov.au",
        "environment.gov.au",
        "finance.gov.au",
        "pm.gov.au",
        "dpmc.gov.au",
        "dss.gov.au",
        "jobsandsmall.business.gov.au",
        "acic.gov.au",
        "afi.gov.au",
        "austrade.gov.au",
        "dfat.gov.au",
        "immi.homeaffairs.gov.au",
        "border.gov.au",
        "comcare.gov.au",
        "apo.gov.au",
        "apsc.gov.au",
        "apvma.gov.au",
        "casa.gov.au",
        "acma.gov.au",
        # Agencies
        "bom.gov.au",
        "abs.gov.au",
        "asic.gov.au",
        "apra.gov.au",
        "accc.gov.au",
        "medicare.gov.au",
        "servicesaustralia.gov.au",
        "ndis.gov.au",
        "tga.gov.au",
        "aihw.gov.au",
        "aemo.com.au",
        "nhmrc.gov.au",
        "nla.gov.au",
        "anao.gov.au",
        "ombudsman.gov.au",
        "oaic.gov.au",
        "fwc.gov.au",
        "asc.gov.au",
        "afsa.gov.au",
        "arpansa.gov.au",
        "gbrmpa.gov.au",
        "aims.gov.au",
        "csiro.au",
        "geoscience.gov.au",
        "ga.gov.au",
        # State agencies
        "revenue.nsw.gov.au",
        "service.nsw.gov.au",
        "planning.nsw.gov.au",
        "transport.nsw.gov.au",
        "police.nsw.gov.au",
        "dpi.nsw.gov.au",
        "health.nsw.gov.au",
        "education.nsw.gov.au",
        "vicroads.vic.gov.au",
        "police.vic.gov.au",
        "dhhs.vic.gov.au",
        "dtf.vic.gov.au",
        "delwp.vic.gov.au",
        "qra.qld.gov.au",
        "tmr.qld.gov.au",
        "police.qld.gov.au",
        "health.qld.gov.au",
        "daf.qld.gov.au",
        "dpti.sa.gov.au",
        "sahealth.sa.gov.au",
        "mainroads.wa.gov.au",
        "health.wa.gov.au",
        "transport.tas.gov.au",
        "health.tas.gov.au",
        "health.nt.gov.au",
        "environment.act.gov.au",
        "health.act.gov.au",
        # Govt enterprises
        "auspost.com.au",
        "nbn.com.au",
        "abc.net.au",
        "sbs.com.au",
        "corporatetravel.gov.au",
        # Courts / legal
        "federalcircuitcourt.gov.au",
        "hcourt.gov.au",
        "adr.gov.au",
        "courts.qld.gov.au",
        "magistratescourt.vic.gov.au",
    }
)

# ── AU MEDIA / LIFESTYLE ────────────────────────────────────────────────────
AU_MEDIA = frozenset(
    {
        "homestolove.com.au",
        "realestate.com.au",
        "domain.com.au",
        "news.com.au",
        "abc.net.au",
        "sbs.com.au",
        "smh.com.au",
        "theage.com.au",
        "9news.com.au",
        "7news.com.au",
        "dailytelegraph.com.au",
        "couriermail.com.au",
        "heraldsun.com.au",
        "perthnow.com.au",
        "adelaidenow.com.au",
        "brisbanetimes.com.au",
        "canberratimes.com.au",
        "theaustralian.com.au",
        "afr.com",
        "theguardian.com",
        "bhg.com",
        "architecturaldigest.com",
        "dwell.com",
        "houzz.com",
        "houzz.com.au",
        # Additional AU mastheads
        "insidenewsau.com.au",
        "aussieblogsreviews.com.au",
        "ntnews.com.au",
        "themercury.com.au",
        "theland.com.au",
        "weeklytimesaustralia.com.au",
        "stockjournal.com.au",
        "frasercoastchronicle.com.au",
        "sunshinecoastdaily.com.au",
        "townsvillebulletin.com.au",
        "cairnspost.com.au",
        "goldcoastbulletin.com.au",
        "geelongadvertiser.com.au",
        "maroondah.com.au",
        "bendigoadvertiser.com.au",
        "bordermail.com.au",
        "illawarramercury.com.au",
        "newcastleherald.com.au",
        "centralwestdailies.com.au",
        "nswcountryhourdaily.com.au",
        # Radio / TV
        "commercialradio.com.au",
        "nova.com.au",
        "kiis.com.au",
        "triplej.net.au",
        "2gb.com.au",
        "3aw.com.au",
        "channelnine.com.au",
        "ten.com.au",
        "channel7.com.au",
        "foxtel.com.au",
        "stan.com.au",
        "binge.com.au",
        "streamotion.com.au",
        # Lifestyle / magazine
        "womensday.com.au",
        "aww.com.au",
        "nowtolove.com.au",
        "escape.com.au",
        "harpersbazaar.com.au",
        "vogue.com.au",
        "better.com.au",
        "kidspot.com.au",
        "mamamia.com.au",
    }
)

# ── AGGREGATORS / DIRECTORIES ────────────────────────────────────────────────
AGGREGATORS = frozenset(
    {
        # Healthcare
        "whatclinic.com",
        "healthengine.com.au",
        "hotdoc.com.au",
        "healthdirect.gov.au",
        "healthshare.com.au",
        "medicaldirector.com.au",
        # General
        "yelp.com",
        "yelp.com.au",
        "hipages.com.au",
        "oneflare.com.au",
        "expertise.com",
        "trustpilot.com",
        "localsearch.com.au",
        "truelocal.com.au",
        "yellowpages.com.au",
        "whitecoat.com.au",
        "servicecentral.com.au",
        "wordofmouth.com.au",
        "startlocal.com.au",
        "productreview.com.au",
        # Trade / task
        "airtasker.com",
        "serviceseeking.com.au",
        "bark.com",
        "taskhero.com.au",
        "tradie.com.au",
        "hireatrade.com.au",
        "tradespeople.com.au",
        "tradesman.com.au",
        "findatrade.com.au",
        # Legal
        "lawsociety.com.au",
        "findlaw.com.au",
        "legalvision.com.au",
        "lawpath.com.au",
        "legalmatch.com.au",
        "lawyerslist.com.au",
        "lawinfoon.com.au",
        "australianlawyer.com.au",
        # Construction
        "masterbuilders.com.au",
        "buildsearch.com.au",
        "architectslist.com.au",
        # Industry bodies / bar associations
        "ada.org.au",
        "ada.org",
        "finder.orthodonticsaustralia.org.au",
        "hia.com.au",
        "aibs.com.au",
        "lawcouncil.asn.au",
        "qls.com.au",
        "vicbar.com.au",
        "austbar.asn.au",
        # Legal / industry media
        "lsj.com.au",
        "lawyersweekly.com.au",
        "lawfoundation.net.au",
        # Real estate
        "realcommercial.com.au",
        "commercialrealestate.com.au",
        "allhomes.com.au",
        "homely.com.au",
        "property.com.au",
        "ratemyagent.com.au",
        "opensquare.com.au",
        "homesales.com.au",
        # Jobs
        "seek.com.au",
        "indeed.com.au",
        "jora.com",
        "careerone.com.au",
        "mycareer.com.au",
        "ethicaljobs.com.au",
        "grad.com.au",
        "prosple.com.au",
        "applyonline.com.au",
        # Events / weddings
        "weddingwire.com.au",
        "easyweddings.com.au",
        "polka-dot-bride.com.au",
        "theknot.com",
        "bridestory.com",
        "weddingsonline.com.au",
        # Food delivery / booking
        "uber.com",
        "ubereats.com",
        "menulog.com.au",
        "doordash.com.au",
        "deliveroo.com.au",
        "quandoo.com.au",
        "dimmi.com.au",
        "opentable.com.au",
        "lunchbox.com.au",
        # Travel
        "tripadvisor.com.au",
        "tripadvisor.com",
        "booking.com",
        "expedia.com.au",
        "wotif.com",
        "lastminute.com.au",
        "hotels.com",
        "airbnb.com.au",
        "stayz.com.au",
        # Finance comparison
        "ratecity.com.au",
        "canstar.com.au",
        "finder.com.au",
        "mozo.com.au",
        "infochoice.com.au",
        "comparethemarket.com.au",
        "iselect.com.au",
        "getcovered.com.au",
        # Insurance comparison
        "insuranceline.com.au",
    }
)

# ── CONSTRUCTION RETAILERS / DISTRIBUTORS ────────────────────────────────────
CONSTRUCTION_RETAILERS = frozenset(
    {
        "bunnings.com.au",
        "trade.bunnings.com.au",
        "beaumont-tiles.com.au",
        "nationaltiles.com.au",
        "totaltools.com.au",
        "sydneytools.com.au",
        "tradetools.com",
        "blackwoods.com.au",
        "rs-online.com",
        "au.rs-online.com",
        "bostik.com.au",
        "selleys.com.au",
        "dulux.com.au",
        "taubmans.com.au",
        "haymes.com.au",
        "wattyl.com.au",
        "mitre10.com.au",
        "homehardware.com.au",
        "reece.com.au",
        "tradelink.com.au",
        "samios.net.au",
        "plumbingsales.com.au",
        "csr.com.au",
        "boral.com.au",
        "jameshardie.com.au",
        "bluescope.com.au",
    }
)

# ── BRANDS / MULTINATIONALS ─────────────────────────────────────────────────
BRANDS = frozenset(
    {
        "invisalign.com.au",
        "colgate.com.au",
        "oralb.com.au",
        "3m.com.au",
        "henryschein.com.au",
        # FMCG multinationals
        "unilever.com.au",
        "pg.com",
        "nestle.com.au",
        "loreal.com.au",
        "johnson.com.au",
        "johnsonandjohnson.com.au",
        "reckitt.com.au",
        "sysco.com.au",
        "gsk.com.au",
        "pfizer.com.au",
        "novartis.com.au",
        "abbvie.com.au",
        "astrazeneca.com.au",
        "sanofi.com.au",
        "cslfehring.com.au",
        # Auto brands
        "toyota.com.au",
        "honda.com.au",
        "ford.com.au",
        "holden.com.au",
        "subaru.com.au",
        "mazda.com.au",
        "hyundai.com.au",
        "kia.com.au",
        "volkswagen.com.au",
        "bmwgroup.com.au",
        "mercedes-benz.com.au",
        "nissan.com.au",
        "mitsubishi.com.au",
        "suzuki.com.au",
        # Tech brands
        "hp.com",
        "lenovo.com",
        "dell.com.au",
        "samsung.com.au",
        "lg.com.au",
        "sony.com.au",
        "panasonic.com.au",
        "canon.com.au",
        "epson.com.au",
        "brother.com.au",
    }
)

# ── INSURANCE / HEALTH FUNDS ────────────────────────────────────────────────
HEALTH_FUNDS = frozenset(
    {
        "bupa.com.au",
        "medibank.com.au",
        "hcf.com.au",
        "nib.com.au",
        "healthpartners.com.au",
        "ahm.com.au",
        "help.ahm.com.au",
        "cbhs.com.au",
        # Additional health funds
        "australianunity.com.au",
        "gmhba.com.au",
        "latrobe.com.au",
        "myhealthpolicies.com.au",
        "phoenixhealthfund.com.au",
        "qantas.com.au",
        "teachers.com.au",
        "teachershealthfund.com.au",
        "westfund.com.au",
        "arhg.com.au",
        "bupa.com",
        "defence.com.au",
        "defencehealthfund.com.au",
        "drivequest.com.au",
        "frank.com.au",
        "healthcareguide.com.au",
        "healthengine.com.au",
        "healthinsurance.com.au",
        "mildura.com.au",
        "nurses.com.au",
        "nursesfamilyhealthinsurance.com.au",
        "oshc.com.au",
        "peacockinsurance.com.au",
        "railway.com.au",
        "ramsayhealth.com.au",
        "rbhsfund.com.au",
        "sgic.com.au",
        "sgio.com.au",
        "sport.com.au",
        "sportshealthinsurance.com.au",
    }
)

# ── FRANCHISE / CHAIN PARENTS ────────────────────────────────────────────────
# Dental chains
DENTAL_CHAINS = frozenset(
    {
        "1300smiles.com.au",
        "primarydental.com.au",
        "maven.dental",
        "mavendental.com.au",
        "pacificsmiles.com.au",
        "smilepath.com.au",
        "stjohnhealth.com.au",
        "dentalcorp.com.au",
        "nationaldentalcare.com.au",
        "bupadental.com.au",
        "nibdental.com.au",
        "smileclub.com.au",
        "dentalone.com.au",
        "marchorthodontics.com.au",
        "totalortho.com.au",
        "rsdentalgroup.com.au",
        "smilesolutions.com.au",
        "mcdental.com.au",
        "odontologie.com.au",
        "smileteam.com.au",
        "dentalboutique.com.au",
        "allon4.com.au",
        "myimplantdentist.com.au",
    }
)

# Construction chains
CONSTRUCTION_CHAINS = frozenset(
    {
        "metricon.com.au",
        "henleyhomes.com.au",
        "porterdavis.com.au",
        "mainstreetbuilders.com.au",
        "simonds.com.au",
        "burbank.com.au",
        "carlislegroup.com.au",
        "ablgroup.com.au",
        "lendlease.com.au",
        "hutchinsonbuilders.com.au",
        "multiplex.global",
        "probuild.com.au",
        "watpac.com.au",
        "mirvac.com.au",
        "stockland.com.au",
        "mcdonaldjoneshomes.com.au",
        # Additional large developers
        "avjennings.com.au",
        "frasersproperty.com.au",
        "dexus.com",
        "capitallots.com.au",
        "peetlimited.com.au",
        "fkp.com.au",
        "nationalresidential.com.au",
        "summitcorporation.com.au",
        "bestlink.com.au",
        "clarendonhomes.com.au",
        "wbyhomes.com.au",
        "avantiresidential.com.au",
        "weekeshomes.com.au",
        "sievert.com.au",
        "hotondo.com.au",
        "dale-alcock.com.au",
    }
)

# Legal chains
LEGAL_CHAINS = frozenset(
    {
        "slatergordon.com.au",
        "mauriceblackburn.com.au",
        "shineapp.com.au",
        "shinelawyers.com.au",
        "shine.com.au",
        "gordonlegal.com.au",
        "holdingredlich.com",
        "hallandwilcox.com.au",
        "minterellison.com",
        "allens.com.au",
        "claytonutz.com",
        "corrs.com.au",
        "herbertsmithfreehills.com",
        "ashurst.com",
        "kingwood.com.au",
        "gilberttobin.com",
        "nortonrosefulbright.com",
        "hwlebsworth.com.au",
        "lawpartners.com.au",
        # D2 drops
        "gtlaw.com.au",
        "landers.com.au",
        # Additional BigLaw / national chains
        "dwf.law",
        "dentons.com",
        "bakermckenzie.com",
        "squirepattonboggs.com",
        "gadens.com",
        "hwle.com.au",
        "colemanhgreig.com.au",
        "millshowley.com.au",
        "bartier.com.au",
        "piper.com.au",
        "blakekent.com.au",
        "russellkennedy.com.au",
        "andersonadams.com.au",
        "klgates.com",
        "jones.day",
        "freshfields.com",
        "linklaters.com",
        "cliffordchance.com",
        "allenovery.com",
        "whitecaseonline.com",
        "bryanscave.com",
        "hfw.com",
        "turnerfreeman.com.au",
        "keddieslaw.com.au",
        "mclaughlinslaw.com.au",
    }
)

# Auto franchise chains
AUTO_CHAINS = frozenset(
    {
        "ultratune.com.au",
        "midas.com.au",
        "bobjane.com.au",
        "strathfieldcardepot.com.au",
        "kwikfit.com.au",
        "jarcar.com.au",
        "repco.com.au",
        "supercheapauto.com.au",
        "autobarn.com.au",
        # Additional auto chains
        "peterpanagopoulos.com.au",
        "peddersbrakesauto.com.au",
        "peddersauto.com.au",
        "kmart-tyre.com.au",
        "jaxtyres.com.au",
        "mytyres.com.au",
        "tyrequeen.com.au",
        "ozzytyres.com.au",
        "jaxquickfit.com.au",
        "autonexus.com.au",
        "bradythomes.com.au",
        "berrimahholden.com.au",
        "carmarket.com.au",
        "manheimauctions.com.au",
        "grays.com.au",
        "pickles.com.au",
        "motorweb.com.au",
        "redbook.com.au",
        "carsales.com.au",
        "carsguide.com.au",
        "drive.com.au",
        "autotrader.com.au",
        "gumtree.com.au",
        "cars.com.au",
    }
)

# Non-AU dental tourism / foreign clinics
FOREIGN_CLINICS = frozenset(
    {
        "bangkokdentalcenter.com",
        "adalyadentalclinic.com",
    }
)

# Fitness chains
FITNESS_CHAINS = frozenset(
    {
        "fernwoodfitness.com.au",
        "anytimefitness.com.au",
        "f45training.com.au",
        "snapfitness.com.au",
        "fitnessfirst.com.au",
        "planetfitness.com.au",
        "planetfitnessaustralia.com.au",
        "orangetheory.com.au",
        "goodlifehealthclubs.com.au",
        "plus.com.au",
        "vaboretum.com.au",
        "goldsgym.com.au",
        "worldgym.com.au",
        "worldgymaustralia.com.au",
        "24hourfitness.com.au",
        "curves.com.au",
        "jettsfitness.com.au",
        "zap.fitness",
        "clubfitness.com.au",
        "dynamofitness.com.au",
        "gymdirect.com.au",
        "genesisfitness.com.au",
        "virginactive.com.au",
        # D2 drop
        "plusfitness.com.au",
        # Additional chains
        "coreplus.com.au",
        "bodyfit.com.au",
        "barrys.com.au",
        "jetts.com.au",
        "sealsfitness.com.au",
        "viva-leisure.com.au",
        "fitnation.com.au",
        "1fitness.com.au",
        "activelifestyle.com.au",
        "fusefitness.com.au",
        "grexgym.com.au",
        "empowergym.com.au",
        "tigerfitness.com.au",
        "evolutiongym.com.au",
        "cfbyronbay.com.au",
        "crossfit.com.au",
        "cfm.com.au",
    }
)

# Food/restaurant chains
FOOD_CHAINS = frozenset(
    {
        "pizzahut.com.au",
        "dominos.com.au",
        "mcdonalds.com.au",
        "kfc.com.au",
        "hungryjacks.com.au",
        "guzmanygomez.com.au",
        "subway.com.au",
        "redrooster.com.au",
        "oporto.com.au",
        "nandos.com.au",
        "zambrero.com.au",
        "madmex.com.au",
        "grilld.com.au",
        "bettys.com.au",
        "sanschurro.com.au",
        "theboathousergroup.com.au",
        "stellarestaurants.com.au",
        "merivale.com.au",
        "nrg.com.au",
        # Additional chains
        "starbucks.com.au",
        "gloriajeansaustralia.com.au",
        "sanchez.com.au",
        "sushitrain.com.au",
        "bakersdelight.com.au",
        "brumbys.com.au",
        "muffinbreak.com.au",
        "michels.com.au",
        "chatime.com.au",
        "gongcha.com.au",
        "easyway.com.au",
        "schnitz.com.au",
        "saltsmeats.com.au",
        "chicken-treat.com.au",
        "lenardschicken.com.au",
        "rolldsaustralia.com.au",
        "sushiemporium.com.au",
        "noodlebox.com.au",
        "saladbar.com.au",
        "thirstycamel.com.au",
        "bottlemart.com.au",
        "montesrestaurant.com.au",
        "outbacksteakhouse.com.au",
        "hoodoobbq.com.au",
        "grillhaus.com.au",
        "thebowlorama.com.au",
        "oporto.com",
        "redrooster.com",
        "wendys.com.au",
        "burgerfuel.com.au",
        "theburgercollective.com.au",
        "bettysburgers.com.au",
        "holeman-finch.com.au",
        "mrburger.com.au",
        "hatchburgers.com.au",
        "smokedbarbecue.com.au",
    }
)

# Media companies / publishing / directories
MEDIA_COMPANIES = frozenset(
    {
        "news.com.au",
        "abc.net.au",
        "sbs.com.au",
        "gourmettraveller.com.au",
        "delicious.com.au",
        "broadsheet.com.au",
        "timeout.com",
        "urbanlist.com",
        "concreteplayground.com",
        "bestrestaurants.com.au",
        "goodfood.com.au",
        "theguardian.com",
        "stylemagazines.com.au",
        "frankie.com.au",
        "monocle.com",
        "yellowpages.com.au",
        "truelocal.com.au",
        "localsearch.com.au",
        "whitecoat.com.au",
        "hotdoc.com.au",
        "healthengine.com.au",
        "quandoo.com.au",
        "dimmi.com.au",
        "opentable.com.au",
    }
)

# ── ACCOUNTING CHAINS ────────────────────────────────────────────────────────
ACCOUNTING_CHAINS = frozenset(
    {
        "pwc.com.au",
        "bdo.com.au",
        "cpaaustralia.com.au",
        "grantthornton.com.au",
        "bentleys.com.au",
        "taxstore.com.au",
        "mlc.com.au",
        "smart.com.au",
        "oneclicklife.com.au",
        "maxxia.com.au",
        "iorder.com.au",
        "deloitte.com.au",
        "kpmg.com.au",
        "ey.com",
        # D2 drop
        "etax.com.au",
        # Additional accounting chains
        "hrblock.com.au",
        "taxsmart.com.au",
        "accountantsplus.com.au",
        "banksa.com.au",
        "moodysams.com.au",
        "pitcher.com.au",
        "wiseaccounting.com.au",
        "iaccountant.com.au",
        "rsm.com.au",
        "nexia.com.au",
        "williamshart.com.au",
        "hollingsworth.com.au",
        "wac.com.au",
        "bbf.com.au",
        "blairgorman.com.au",
        "maccouns.com.au",
        "hallandcotter.com.au",
        "evershed.com.au",
        "logicca.com.au",
        "perks.com.au",
        "shaw.com.au",
        "bdoaustralia.com.au",
    }
)

# ── GOVERNMENT HEALTH ─────────────────────────────────────────────────────────
GOVERNMENT_HEALTH = frozenset(
    {
        "ipchealth.com.au",
        "dental.mthc.com.au",
        "elizabethmedicalcentre.com.au",
        "sawater.com.au",
    }
)

# ── INDUSTRIAL WHOLESALE ─────────────────────────────────────────────────────
INDUSTRIAL_WHOLESALE = frozenset(
    {
        "holmanindustries.com.au",
        "store.brita.com.au",
        "megt.com.au",
        "actrol.com.au",
        "completehomefiltration.com.au",
        # Additional
        "blackwoods.com.au",
        "tradetools.com.au",
        "toolmart.com.au",
        "protector.com.au",
        "coregas.com.au",
        "airgas.com.au",
        "weldingdepot.com.au",
        "alliedbrands.com.au",
        "bulkfoodwarehouse.com.au",
    }
)

# ── AU BANKS & FINANCE (NEW) ─────────────────────────────────────────────────
AU_BANKS_FINANCE = frozenset(
    {
        # Big 4
        "commbank.com.au",
        "anz.com.au",
        "nab.com.au",
        "westpac.com.au",
        # Regional banks
        "bankwest.com.au",
        "bendigobank.com.au",
        "macquarie.com.au",
        "ing.com.au",
        "bankofqueensland.com.au",
        "suncorp.com.au",
        "mebank.com.au",
        "ubank.com.au",
        "bankaust.com.au",
        "gatewaybank.com.au",
        "newcastlepermanent.com.au",
        "greaterbank.com.au",
        "rabobank.com.au",
        "hsbc.com.au",
        "citibank.com.au",
        "commonwealthbank.com.au",
        "nzbankingsolutions.com.au",
        "stgeorge.com.au",
        "bom.com.au",
        "banksa.com.au",
        "bankofmelbourne.com.au",
        "adelaidebankltd.com.au",
        "heritagefoundation.com.au",
        "movebank.com.au",
        "unity.com.au",
        "tmbank.com.au",
        "firstmac.com.au",
        "resimac.com.au",
        # Mortgage brokers (national)
        "aussie.com.au",
        "loanmarket.com.au",
        "mortgage-choice.com.au",
        "yellowbrickroad.com.au",
        # Insurance giants
        "iag.com.au",
        "qbe.com.au",
        "allianz.com.au",
        "zurich.com.au",
        "aig.com.au",
        "aami.com.au",
        "nrma.com.au",
        "gio.com.au",
        "suncorpinsurance.com.au",
        "racv.com.au",
        "rac.com.au",
        "racq.com.au",
        "ract.com.au",
        "raa.com.au",
        "aant.com.au",
        # Super funds
        "australiansuper.com",
        "rest.com.au",
        "aware.com.au",
        "cbus.com.au",
        "hesta.com.au",
        "hostplus.com.au",
        "sunsuper.com.au",
        "visionsuper.com.au",
        "equipsuper.com.au",
        "caresuper.com.au",
        "lucrf.com.au",
        "mtaasuper.com.au",
        "legalsuper.com.au",
        "unisuper.com.au",
        "tasplan.com.au",
        # Finance aggregators
        "afgonline.com.au",
        "ratecity.com.au",
        "canstar.com.au",
        "finder.com.au",
        "mozo.com.au",
        "infochoice.com.au",
        "comparethemarket.com.au",
        "iselect.com.au",
        # BNPL / fintech
        "afterpay.com",
        "zip.co",
        "humm.com.au",
        "laybuy.com",
        "latitude.com.au",
        "openpay.com.au",
        # ASX-listed financial services
        "macquariegroup.com",
        "amp.com.au",
        "asgard.com.au",
        "mlc.com.au",
        "moneyme.com.au",
    }
)

# ── RETAIL CHAINS (NEW) ──────────────────────────────────────────────────────
RETAIL_CHAINS = frozenset(
    {
        # Supermarkets
        "woolworths.com.au",
        "coles.com.au",
        "aldi.com.au",
        "iga.com.au",
        "costco.com.au",
        "foodland.com.au",
        "supabarn.com.au",
        "spudshed.com.au",
        # Hardware
        "bunnings.com.au",
        "mitre10.com.au",
        "totaltools.com.au",
        "sydneytools.com.au",
        # Department stores
        "kmart.com.au",
        "target.com.au",
        "bigw.com.au",
        "myer.com.au",
        "davidjones.com.au",
        "davidjones.com",
        "harris.com.au",
        "harrisscarfe.com.au",
        # Electronics
        "jbhifi.com.au",
        "harveynorman.com.au",
        "thegoodguys.com.au",
        "officeworks.com.au",
        "aplusinc.com.au",
        "dicksmith.com.au",
        "bing.lee.com.au",
        "techfast.com.au",
        "pbtech.com.au",
        # Fashion
        "cottonon.com",
        "countryroad.com.au",
        "kathmandu.com.au",
        "rebelsport.com.au",
        "rebel.com.au",
        "theiconic.com.au",
        "asos.com.au",
        "gluestore.com.au",
        "rstyle.com.au",
        "calibre.com.au",
        "saba.com.au",
        "cue.com.au",
        "witchery.com.au",
        "dotti.com.au",
        "jeanswest.com.au",
        "rockyourwardrobe.com.au",
        "sportsgirl.com.au",
        "sussan.com.au",
        "millers.com.au",
        "crossroads.com.au",
        "citybeach.com.au",
        "billabong.com.au",
        "roxy.com.au",
        "rip-curl.com",
        "quicksilver.com.au",
        "converse.com.au",
        "vans.com.au",
        "nike.com.au",
        "adidas.com.au",
        "puma.com.au",
        "reebok.com.au",
        "newbalance.com.au",
        "asics.com.au",
        "skechers.com.au",
        "clarks.com.au",
        "bata.com.au",
        "ugg.com.au",
        "timberland.com.au",
        # Pharmacy
        "chemistwarehouse.com.au",
        "priceline.com.au",
        "terrywhite.com.au",
        "chempro.com.au",
        "pharmacyonline.com.au",
        "pharmacy4less.com.au",
        "blooms.com.au",
        "good-price-pharmacy.com.au",
        "amcal.com.au",
        "guardian.com.au",
        # Auto parts
        "supercheapauto.com.au",
        "repco.com.au",
        "autobarn.com.au",
        # Pet
        "petbarn.com.au",
        "petstock.com.au",
        "petshed.com.au",
        "animates.com.au",
        # Furniture / homewares
        "ikea.com.au",
        "fantastic.com.au",
        "amart.com.au",
        "freedom.com.au",
        "nickscali.com.au",
        "harvey-norman.com.au",
        "oz-design.com.au",
        "domayne.com.au",
        "bcf.com.au",
        "anaconda.com.au",
        # Liquor
        "danmurphys.com.au",
        "bws.com.au",
        "liquorland.com.au",
        "firstchoiceliquor.com.au",
        "bottlemart.com.au",
        "cellarmasters.com.au",
        # Toys / kids
        "toyworld.com.au",
        "toyuniverse.com.au",
        "mothersbaby.com.au",
        "babybunting.com.au",
        # Books / music
        "dymocks.com.au",
        "qbdbooks.com.au",
        "angusrobertson.com.au",
        "booktopia.com.au",
        # Outdoor / camping
        "snowys.com.au",
        "tentworld.com.au",
        "campsaver.com.au",
        # Jewellery
        "michaelhill.com.au",
        "tiffany.com.au",
        "lovisa.com.au",
        "prouds.com.au",
        "anguscoote.com.au",
        # Optometry chains
        "specsavers.com.au",
        "opsm.com.au",
        "baileynelson.com.au",
        "laubman-pank.com.au",
        "clearly.com.au",
        "vision-works.com.au",
        "eyesite.com.au",
        # Stationery / office
        "staples.com.au",
    }
)

# ── TELCO & UTILITIES (NEW) ──────────────────────────────────────────────────
TELCO_UTILITIES = frozenset(
    {
        # Telcos
        "telstra.com.au",
        "optus.com.au",
        "tpg.com.au",
        "vodafone.com.au",
        "amaysim.com.au",
        "boost.com.au",
        "belong.com.au",
        "iiinet.net.au",
        "internode.on.net",
        "dodo.com.au",
        "exetel.com.au",
        "aussiebroadband.com.au",
        "spintel.com.au",
        "vividwireless.com.au",
        "lebara.com.au",
        "aldimobile.com.au",
        "telcoin.com.au",
        "yomojo.com.au",
        "woolworthsmobile.com.au",
        "colesamaysim.com.au",
        "kogan.com.au",
        "mate.com.au",
        "superloop.com.au",
        "harbournetworks.com.au",
        "pennytel.com.au",
        # Energy
        "agl.com.au",
        "energyaustralia.com.au",
        "originenergy.com.au",
        "ergon.com.au",
        "ausgrid.com.au",
        "sapowernetworks.com.au",
        "powerlinks.com.au",
        "endeavourenergy.com.au",
        "jemena.com.au",
        "unity.com.au",
        "simplybusiness.com.au",
        "lumo.com.au",
        "covau.com.au",
        "simply-energy.com.au",
        "redenergy.com.au",
        "momentumenergy.com.au",
        "powershop.com.au",
        "alintaenergy.com.au",
        "enova.com.au",
        "clickenergy.com.au",
        "elysianenergy.com.au",
        "tango.com.au",
        # Water
        "sydneywater.com.au",
        "melbournewater.com.au",
        "seqwater.com.au",
        "sawater.com.au",
        "waternsw.com.au",
        "gwmwater.com.au",
        "coliban.com.au",
        "goulburnmurray.com.au",
        "citywestwater.com.au",
        "westernwater.com.au",
        "yarra.com.au",
        "pattersoncorp.com.au",
        # Gas
        "evoenergy.com.au",
        "atco.com.au",
        "agig.com.au",
        "multinet.com.au",
        # Internet / NBN resellers (large national only)
        "melbourneit.com.au",
        "vocus.com.au",
        "nextgen.com.au",
        "swiftnetworks.com.au",
    }
)

# ── EDUCATION (NEW) ──────────────────────────────────────────────────────────
EDUCATION = frozenset(
    {
        # Go8 universities
        "sydney.edu.au",
        "unimelb.edu.au",
        "anu.edu.au",
        "unsw.edu.au",
        "uq.edu.au",
        "monash.edu",
        "uwa.edu.au",
        "adelaide.edu.au",
        # Other universities
        "uts.edu.au",
        "rmit.edu.au",
        "qut.edu.au",
        "griffith.edu.au",
        "deakin.edu.au",
        "latrobe.edu.au",
        "curtin.edu.au",
        "wollongong.edu.au",
        "swinburne.edu.au",
        "bond.edu.au",
        "cdu.edu.au",
        "flinders.edu.au",
        "newcastle.edu.au",
        "murdoch.edu.au",
        "jcu.edu.au",
        "canberra.edu.au",
        "acu.edu.au",
        "utas.edu.au",
        "une.edu.au",
        "usq.edu.au",
        "scu.edu.au",
        "ecu.edu.au",
        "westernsydney.edu.au",
        "federation.edu.au",
        "csu.edu.au",
        "vu.edu.au",
        "cqu.edu.au",
        "torrens.edu.au",
        "avondale.edu.au",
        "charles-sturt.edu.au",
        "usc.edu.au",
        # TAFE
        "tafensw.edu.au",
        "tafe.nsw.edu.au",
        "tafeqld.edu.au",
        "tafe.qld.edu.au",
        "gotafe.vic.edu.au",
        "holmesglen.edu.au",
        "swtafe.edu.au",
        "nmtafe.wa.edu.au",
        "tafe.net.au",
        "tafeaustralia.edu.au",
        # Private colleges
        "navitas.com",
        "navitas.com.au",
        "aftrs.edu.au",
        "nida.edu.au",
        "aicd.com.au",
        "mgsm.edu.au",
        "mit.edu.au",
        "aic.edu.au",
        # School chains
        "goodshepherd.edu.au",
        "catholicschools.edu.au",
        "sydneycatholicschools.edu.au",
        "ccg.nsw.edu.au",
        "baulkhamhills.edu.au",
        # Online / for-profit
        "openuniversities.edu.au",
        "openuniversities.com.au",
        "study.com.au",
        "lms.edu.au",
        "upskilled.edu.au",
        "universityofexcel.com.au",
        "coursera.org",
        "udemy.com",
        "linkedin.com",
    }
)

# ── HOSPITALS & HEALTH NETWORKS (NEW) ────────────────────────────────────────
HOSPITALS_HEALTH_NETWORKS = frozenset(
    {
        # Public / gov networks
        "alfredhealth.org.au",
        "melbournehealth.org.au",
        "austin.org.au",
        "barwonhealth.org.au",
        "svha.org.au",
        "slhd.nsw.gov.au",
        "seslhd.health.nsw.gov.au",
        "nnswlhd.health.nsw.gov.au",
        "islhd.health.nsw.gov.au",
        "nbmlhd.health.nsw.gov.au",
        "mclhd.health.nsw.gov.au",
        "hnehealth.nsw.gov.au",
        "swslhd.health.nsw.gov.au",
        "wslhd.health.nsw.gov.au",
        "cclhd.health.nsw.gov.au",
        "health.act.gov.au",
        # Private hospital groups
        "ramsayhealth.com",
        "ramsayhealth.com.au",
        "healthscope.com.au",
        "epworth.org.au",
        "calvarycare.org.au",
        "calvary.com.au",
        "cabrinihealth.com.au",
        "stvincentsprivate.com.au",
        "stvincents.com.au",
        "monashhealthaustralia.org.au",
        "benemedical.com.au",
        "nationalrehab.com.au",
        "healthecare.com.au",
        "mater.org.au",
        "smh.com.au",
        "royalchildrenshospital.gov.au",
        "rch.org.au",
        "schn.health.nsw.gov.au",
        "wch.sa.gov.au",
        "pch.health.wa.gov.au",
        # National chains
        "medicalcentres.com.au",
        "primaryhealth.com.au",
        "sshealth.com.au",
        "healthicare.com.au",
        "nationwideprimary.com.au",
        # Health funds (already in HEALTH_FUNDS, duplicates OK — union deduplicates)
        "medibank.com.au",
        "bupa.com.au",
        "hcf.com.au",
        "nib.com.au",
        # Pathology / radiology chains
        "sydneypathology.com.au",
        "sullivan-nicolaides.com.au",
        "qml.com.au",
        "clinicallabs.com.au",
        "douglashanly.com.au",
        "mldx.com.au",
        "primeradiology.com.au",
        "i-med.com.au",
        "specialist-radiology.com.au",
        "mia.com.au",
        "capitalradiology.com.au",
        "healthscope-pathology.com.au",
        # Pharmacy chains
        "chemistwarehouse.com.au",
        "priceline.com.au",
        "terrywhite.com.au",
    }
)

# ── FRANCHISE HOME SERVICES (NEW) ────────────────────────────────────────────
FRANCHISE_HOME_SERVICES = frozenset(
    {
        # Jim's Group
        "jimsmowing.com.au",
        "jimscleaning.com.au",
        "jimsfencing.com.au",
        "jimsantennas.com.au",
        "jimsgroup.com.au",
        "jims.net",
        "jimspainting.com.au",
        "jimsbuildingmaintenance.com.au",
        "jimspestcontrol.com.au",
        "jimsroofingandfacades.com.au",
        "jimstreeservices.com.au",
        "jimsmobile.com.au",
        "jimselectrical.com.au",
        "jimscomputerservices.com.au",
        "jimsgarages.com.au",
        "jimshomeservices.com.au",
        # VIP
        "viphomeservices.com.au",
        "vipfranchise.com.au",
        # Hire A Hubby / handyman
        "hubbyhubbyhome.com.au",
        "hireoption.com.au",
        "fixr.com.au",
        "handymanconnect.com.au",
        # Pool / cleaning / specialised
        "poolwerx.com.au",
        "swimart.com.au",
        "electrodry.com.au",
        "ozcarpetcleaning.com.au",
        "jims.net.au",
        "vipclean.com.au",
        "myclean.com.au",
        "helpling.com.au",
        # Pest control chains
        "pestie.com.au",
        "termiquit.com.au",
        "pestclear.com.au",
        "termite.com.au",
        "arrow.com.au",
        # Locksmith chains
        "openandshut.com.au",
        # Security chains
        "crimsafe.com.au",
        "protectall.com.au",
        "adtaustralia.com.au",
        # Moving chains
        "moveme.com.au",
        "removals.com.au",
        "muval.com.au",
        # O'Brien Glass
        "o-brien.com.au",
        "obrienautoglass.com.au",
        # Snap / drain / plumbing chains
        "snappyplumbing.com.au",
        "mrplumber.com.au",
        "victorianplumbing.com.au",
    }
)

# ── TRANSPORT & LOGISTICS CHAINS (NEW) ───────────────────────────────────────
TRANSPORT_CHAINS = frozenset(
    {
        # Airlines
        "qantas.com.au",
        "jetstar.com.au",
        "virginaustralia.com.au",
        "tigerair.com.au",
        "rex.com.au",
        "bonzaairlines.com.au",
        "flybonza.com.au",
        # Rail / bus
        "sydneytrains.info",
        "transportnsw.info",
        "ptv.vic.gov.au",
        "translink.com.au",
        "transwa.wa.gov.au",
        "greyhound.com.au",
        "firefly.com.au",
        # Ride share
        "uber.com.au",
        "didi.com.au",
        "ola.com.au",
        # Freight / logistics
        "auspost.com.au",
        "sendle.com.au",
        "fastway.com.au",
        "aramex.com.au",
        "startrack.com.au",
        "tnt.com.au",
        "fedex.com.au",
        "dhl.com.au",
        "ups.com.au",
        "couriersplease.com.au",
        "allied.com.au",
        "linfox.com.au",
        "toll.com.au",
        "mainfreight.com.au",
        "followmont.com.au",
        "visy.com.au",
        # Car rental / hire
        "hertz.com.au",
        "avis.com.au",
        "budget.com.au",
        "europcar.com.au",
        "sixt.com.au",
        "thrifty.com.au",
        "redspot.com.au",
        "ace.com.au",
        "flexicar.com.au",
        "goget.com.au",
        # Ferry / boat
        "mantaray.com.au",
        "fantasea.com.au",
        # Port / airport authorities
        "sydneyairport.com.au",
        "melbourneairport.com.au",
        "bne.com.au",
        "perthairport.com.au",
        "adelaideairport.com.au",
        "cairnsairport.com.au",
        "goldcoastairport.com.au",
        # Taxis
        "13cabs.com.au",
        "silvertop.com.au",
        "yellowcab.com.au",
        "ingogo.com.au",
        # EV charging
        "chargefox.com.au",
        "evie.com.au",
        "tritiumcharging.com.au",
    }
)

# ── REAL ESTATE & PROPERTY CHAINS (NEW) ──────────────────────────────────────
REAL_ESTATE_CHAINS = frozenset(
    {
        # Portals
        "realestate.com.au",
        "domain.com.au",
        "allhomes.com.au",
        "homely.com.au",
        "property.com.au",
        "realestateview.com.au",
        "ratemyagent.com.au",
        "homesales.com.au",
        "realcommercial.com.au",
        "commercialrealestate.com.au",
        # National franchise networks
        "raywhite.com.au",
        "ljhooker.com.au",
        "harcourts.com.au",
        "mcgrath.com.au",
        "remax.com.au",
        "elders.com.au",
        "century21.com.au",
        "coldwellbanker.com.au",
        "firstnational.com.au",
        "professionals.com.au",
        "prdnationwide.com.au",
        "eves.com.au",
        "barryplant.com.au",
        "nellisgroup.com.au",
        "jellis-craig.com.au",
        "marshall.com.au",
        "bigginscott.com.au",
        "obrienrealestate.com.au",
        "buxton.com.au",
        "stockdaleleggo.com.au",
        "thinkproperty.com.au",
        # Property management platforms
        "managedapp.com.au",
        ":reip.com.au",
        "mybond.com.au",
        "propertyme.com",
        "propertytree.com.au",
        # Auction platforms
        "homepriceguide.com.au",
        "pricefinder.com.au",
        "rpdata.com.au",
        "corelogic.com.au",
        # Commercial / industrial property
        "jll.com.au",
        "cbre.com.au",
        "colliers.com.au",
        "knightfrank.com.au",
        "avison.com.au",
        "burgessrawson.com.au",
        # Conveyancing chains
        "legalconveyancing.com.au",
        "easyconveyancing.com.au",
        "conveyancingworks.com.au",
        # Body corporate / strata
        "strata.com.au",
        "realty.com.au",
        "pacemanagers.com.au",
        # Holiday lettings
        "airbnb.com.au",
        "stayz.com.au",
        "vrbo.com.au",
        "holidayrentals.com.au",
        "visitvictoria.com.au",
    }
)

# ── NATIONAL HEALTHCARE CHAINS — ALLIED HEALTH (NEW) ─────────────────────────
ALLIED_HEALTH_CHAINS = frozenset(
    {
        # Physio chains
        "lifecare.com.au",
        "arthritis.org.au",
        "physiotherapy.asn.au",
        "physiogroup.com.au",
        "bodyfocus.com.au",
        "myphysio.com.au",
        "nationphysio.com.au",
        "physiofusion.com.au",
        "thephysioroom.com.au",
        "physio.com.au",
        "injuryguru.com.au",
        "reboundhealth.com.au",
        # Chiro chains
        "chiropractic.com.au",
        "mychiropractor.com.au",
        "citychiropracticcentre.com.au",
        "fixedbychiropractor.com.au",
        # Psychology / mental health chains
        "mhinvest.com.au",
        "headspace.org.au",
        "beyondblue.org.au",
        "blackdoginstitute.org.au",
        "sane.org",
        "mensline.org.au",
        "lifeline.org.au",
        "betterhelp.com",
        "griefline.org.au",
        "relationships.org.au",
        # Audiology chains
        "amplifon.com.au",
        "hiddenheading.com.au",
        "nationalheadsets.com.au",
        "nationwidehearing.com.au",
        "audiologyaustralia.com.au",
        "bayaudiology.com.au",
        "neurosound.com.au",
        # Podiatry chains
        "podiatry.com.au",
        "thepodiatryclinic.com.au",
        "foothealthpodiatry.com.au",
        # Nutrition / dietetics
        "foodstandards.gov.au",
        "nutritionaustralia.org.au",
        "daa.asn.au",
        # Optical chains (already in RETAIL_CHAINS but unique additions)
        "nrmaoptical.com.au",
        # Pharmacy guild / association
        "guild.org.au",
        "psa.org.au",
        # Community health
        "communityhealth.net.au",
        "primaryhealthnetwork.com.au",
        "centralcoastphn.com.au",
        "murrumbidgeephn.com.au",
        "coordinare.org.au",
        "hn.org.au",
        # Aged care chains
        "mecwacare.org.au",
        "baptistcare.org.au",
        "anglicaresq.org.au",
        "uniting.org",
        "unitingcare.org.au",
        "mercy.com.au",
        "estia.com.au",
        "regis.com.au",
        "aveonhealthcare.com.au",
        "bupa.com.au",
        "japara.com.au",
        "allity.com.au",
        "acacia.com.au",
        "amana.com.au",
        "alzheimers.org.au",
        "springfieldhealthcare.com.au",
        # Disability / NDIS providers (national)
        "aruma.com.au",
        "possability.com.au",
        "stride.com.au",
        "genazzano.com.au",
        "summitcare.com.au",
        "yooralla.com.au",
        "scope.org.au",
        "lifestart.net.au",
        "lifespan.org.au",
        "achieveaustralia.org.au",
        "afford.com.au",
        "endeavour.com.au",
        "nova-employment.com.au",
        "downessyndrome.org.au",
        "cerebralpalsy.org.au",
        "amaze.org.au",
        "autism.org.au",
        # Vet chains
        "greencross.com.au",
        "vca.com.au",
        "vetcare.com.au",
        "vetpartners.com.au",
        "smartvets.com.au",
        "animaltrust.com.au",
        "petsandvets.com.au",
        "australianveterinarians.com.au",
        "vcah.com.au",
    }
)

# ── NATIONAL CHARITY / NFP (NEW) ─────────────────────────────────────────────
CHARITIES_NFP = frozenset(
    {
        "salvationarmy.org.au",
        "redcross.org.au",
        "vicentcare.org.au",
        "vinnies.org.au",
        "anglicare.org.au",
        "missionaustralia.com.au",
        "homelessnessaustralia.org.au",
        "foodbank.org.au",
        "fareshare.net.au",
        "ozfoodbank.org.au",
        "secondbite.org",
        "habitat.org.au",
        "housingstress.com.au",
        "acnc.gov.au",
        "philanthropy.org.au",
        "community.com.au",
        "volunteering.com.au",
        "volunteeringaustralia.org",
        "rspca.org.au",
        "animalaustralia.org",
        "humaneresearch.org.au",
        "wwf.org.au",
        "greenpeace.org.au",
        "acf.org.au",
        "conservation.org.au",
        "ausconservation.org.au",
        "beyondblue.org.au",
        "blackdoginstitute.org.au",
        "mindfull.org.au",
        "ruok.org.au",
        "mensline.org.au",
        "lifeline.org.au",
        "kidshelpline.com.au",
        "smiling-mind.com.au",
        "headspace.org.au",
        "orygen.org.au",
        "reach.org.au",
    }
)

# ── CHILDCARE & EARLY EDUCATION CHAINS (NEW) ─────────────────────────────────
CHILDCARE_CHAINS = frozenset(
    {
        "guardian.com.au",
        "guardianchildcare.com.au",
        "thinkchildcare.com.au",
        "careforkids.com.au",
        "goodstart.org.au",
        "kidsacademy.com.au",
        "sunshineearlylearning.com.au",
        "buddinganimalchildcare.com.au",
        "nurture.com.au",
        "exploreanddiscover.com.au",
        "acecqa.gov.au",
        "startingblocks.gov.au",
        "lifelinechildcare.com.au",
        "theircare.com.au",
        "communitychildcare.com.au",
        "creche-and-kindergarten.com.au",
        "tinychipmunks.com.au",
        "smallwonders.com.au",
        "seedlings.com.au",
        "kindyhaven.com.au",
        "greenstarchildcare.com.au",
        "peppercornkindergarten.com.au",
        "kidsco.com.au",
        "beforeanafter.com.au",
        "campaustralia.com.au",
        "ymca.org.au",
        "pcyc.org.au",
        "scouts.com.au",
        "girlguides.com.au",
        "kidzone.com.au",
        "holidaycare.com.au",
        "oosh.com.au",
        "oshclub.com.au",
        "ymcavic.org.au",
    }
)

# ── GAMBLING & GAMING CHAINS (NEW) ───────────────────────────────────────────
GAMBLING_CHAINS = frozenset(
    {
        # Wagering
        "tabcorp.com.au",
        "tab.com.au",
        "sportsbet.com.au",
        "bet365.com.au",
        "ladbrokes.com.au",
        "neds.com.au",
        "pointsbet.com.au",
        "betfair.com.au",
        "unibet.com.au",
        "williamhill.com.au",
        "palmerbet.com.au",
        "topbetta.com.au",
        "boombet.com.au",
        "draftstars.com.au",
        "topsport.com.au",
        "bluebet.com.au",
        "elitebet.com.au",
        # Lottery
        "thelott.com",
        "ozlotteries.com",
        "melbournemelbourne.com.au",
        "goldenlotteries.com.au",
        "nsw-lotteries.com.au",
        "tatlotteries.com.au",
        "ntlotteries.com.au",
        # Casinos
        "crowncasino.com.au",
        "starcasino.com.au",
        "skycity.com.au",
        "jupiters.com.au",
        "thecrown.com.au",
        "thestar.com.au",
        "boardwalkcasino.com.au",
        "mindilbeach.com.au",
        # Gaming / poker machines
        "aristocrat.com",
        "igt.com.au",
        # Responsible gambling
        "gambleaware.nsw.gov.au",
        "gamblinghelponline.net.au",
        "responsiblegambling.vic.gov.au",
    }
)

# ── SPORTING ORGS & NATIONAL CLUBS (NEW) ─────────────────────────────────────
SPORTING_ORGS = frozenset(
    {
        # National sports bodies
        "cricket.com.au",
        "afl.com.au",
        "nrl.com.au",
        "ffa.com.au",
        "footballaustralia.com.au",
        "tennis.com.au",
        "swimming.org.au",
        "athletics.com.au",
        "cycling.org.au",
        "golf.org.au",
        "netball.com.au",
        "basketball.net.au",
        "volleyball.org.au",
        "rugby.com.au",
        "rugbyaustralia.com.au",
        "bowls.com.au",
        "archery.org.au",
        "shooting.org.au",
        "triathlon.org.au",
        "rowing.org.au",
        "canoe.org.au",
        "gymnastics.org.au",
        "weightlifting.org.au",
        "boxing.org.au",
        "surfingaustralia.com",
        "surfingaustralia.com.au",
        "snowaustralia.com.au",
        "equestrian.org.au",
        # Major club chains / league pages
        "collingwoodfc.com.au",
        "essendonfc.com.au",
        "richmondfc.com.au",
        "hawthorn.com.au",
        "geelongcats.com.au",
        "carltonfc.com.au",
        "westernbulldogs.com.au",
        "stkildafc.com.au",
        "brisbanelions.com.au",
        "sydneyswans.com.au",
        "gws.com.au",
        "fremantlefc.com.au",
        "westcoasteagles.com.au",
        "portadelaidefc.com.au",
        "adelaidecrows.com.au",
        "nthmelbourne.com.au",
        "goldcoastsuns.com.au",
        # NRL clubs
        "broncos.com.au",
        "bulldogs.com.au",
        "rabbitohs.com.au",
        "roosters.com.au",
        "eels.com.au",
        "panthers.com.au",
        "raiders.com.au",
        "stgeorgeillawarradragons.com.au",
        "sharks.com.au",
        "tigers.com.au",
        "knights.com.au",
        "storm.com.au",
        "manlyseaeagles.com.au",
        # A-League
        "melbournecity.com.au",
        "melbournevictory.com.au",
        "sydneyfc.com.au",
        "wsw.com.au",
        "cityfc.com.au",
        # Olympic / Commonwealth
        "olympics.com.au",
        "aoc.com.au",
        "paralympics.org.au",
        "commgames.com.au",
        # Stadiums / venues
        "mcg.org.au",
        "accor-stadium.com.au",
        "scg.com.au",
        "gabba.com.au",
        "optus-stadium.com.au",
        "accorhotels-arena.com.au",
        "raceground.com.au",
        # Racing
        "racing.com.au",
        "vrc.net.au",
        "ajc.org.au",
        "thoroughbred.com.au",
        "harness.org.au",
        "racingqueensland.com.au",
        "greyhoundaustralia.org.au",
        "greyhoundsaustralia.com.au",
    }
)

# ── COMBINED SET (for exact/subdomain match) ─────────────────────────────────
BLOCKED_DOMAINS: frozenset[str] = (
    SOCIAL_PLATFORMS
    | TECH_GIANTS
    | WEBSITE_BUILDERS
    | HOSTING_INFRA
    | AU_GOVERNMENT
    | AU_MEDIA
    | AGGREGATORS
    | CONSTRUCTION_RETAILERS
    | BRANDS
    | HEALTH_FUNDS
    | DENTAL_CHAINS
    | CONSTRUCTION_CHAINS
    | LEGAL_CHAINS
    | AUTO_CHAINS
    | FOREIGN_CLINICS
    | FITNESS_CHAINS
    | FOOD_CHAINS
    | MEDIA_COMPANIES
    | ACCOUNTING_CHAINS
    | GOVERNMENT_HEALTH
    | INDUSTRIAL_WHOLESALE
    |
    # New D2.1A categories
    AU_BANKS_FINANCE
    | RETAIL_CHAINS
    | TELCO_UTILITIES
    | EDUCATION
    | HOSPITALS_HEALTH_NETWORKS
    | FRANCHISE_HOME_SERVICES
    | TRANSPORT_CHAINS
    | REAL_ESTATE_CHAINS
    | ALLIED_HEALTH_CHAINS
    | CHARITIES_NFP
    | CHILDCARE_CHAINS
    | GAMBLING_CHAINS
    | SPORTING_ORGS
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
