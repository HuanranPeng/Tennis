#!/usr/bin/env python3
"""
Apply SEO patches to the local static site.

Idempotent: detects its own sentinel markers and re-applies cleanly.

Run standalone:
    python3 scripts/apply_seo.py

Tasks covered:
  01 Summer Camp page          02 Homepage              03 Coaches page
  04 Group Lessons page        05 Programs page         06 Contact page
  07 Schema injection (JSON-LD)   08 Image alt text + global footer cleanup
  09 Summer camp splash overlay  10 Tab favicon (site logo)
"""
from __future__ import annotations

import html as html_lib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SENTINEL = "data-upa-seo"

# Full-screen summer camp promo (stripped + re-injected each `apply_seo` run).
SUMMER_SPLASH_HTML = """<!--upa-summer-splash-->
<div class="upa-summer-splash" id="upa-summer-splash" role="dialog" aria-modal="true" aria-label="2026 summer camp" hidden>
  <div class="upa-summer-splash__backdrop" data-close-splash tabindex="-1"></div>
  <div class="upa-summer-splash__panel">
    <button type="button" class="upa-summer-splash__close" data-close-splash aria-label="Close">&times;</button>
    <img class="upa-summer-splash__img" src="assets/site/2026-summer-camp-flyer.png" alt="2026 Ultra Performance Academy summer tennis camp flyer" loading="eager" decoding="async" width="800" height="1030">
    <div class="upa-summer-splash__actions">
      <a href="summerholiday-camp.html#camp-2026" class="upa-summer-splash__cta">View camp details</a>
      <button type="button" class="upa-summer-splash__later" data-close-splash>Not now</button>
    </div>
  </div>
</div>
<script defer src="assets/site/summer-camp-splash.js"></script>
<!--/upa-summer-splash-->
"""
# Same asset as the header logo (Hostinger export).
SITE_TAB_LOGO = "assets/site/transparent1-YbNB6q61jjSn7eRZ.png"
FAVICON_HTML = f"""<!--upa-favicon-->
<link rel="icon" type="image/png" sizes="32x32" href="{SITE_TAB_LOGO}">
<link rel="icon" type="image/png" sizes="192x192" href="{SITE_TAB_LOGO}">
<link rel="apple-touch-icon" href="{SITE_TAB_LOGO}">
<!--/upa-favicon-->
"""
SITE_BASE = "https://huanranpeng.github.io/Tennis"
SITE_HOME = SITE_BASE + "/"

DEFAULT_OG_IMAGE = SITE_BASE + "/assets/site/2026-summer-camp-flyer.png"

CLEAN_INSTAGRAM = "https://www.instagram.com/ultra.performance.academy"
PHONE = "(650) 308-8355"
ADDRESS_HTML = (
    'Mission College, 3000 Mission College Boulevard, Santa Clara, CA 95054'
)


def page_url(slug: str) -> str:
    """Canonical URL for a page on the GitHub Pages mirror."""
    if slug == "home":
        return SITE_HOME
    return f"{SITE_BASE}/{slug}.html"


# ---------------------------------------------------------------------------
# Per-page SEO configuration
# ---------------------------------------------------------------------------

PAGES: dict[str, dict] = {
    "index.html": {
        "slug": "home",
        "title": "Tennis Lessons in Santa Clara & Bay Area | Ultra Performance Academy",
        "description": (
            "Ultra Performance Academy offers expert tennis lessons in Santa Clara, CA. "
            "Founded by Stephanie Huang, our USTA-certified coaches provide private lessons, "
            "group clinics, and summer camps for kids, juniors, and adults throughout the Bay "
            "Area. Located at Mission College. Call (650) 308-8355."
        ),
        "keywords": (
            "tennis lessons santa clara, bay area tennis coach, Stephanie Huang, "
            "private tennis lessons, kids tennis lessons, junior tennis academy, "
            "silicon valley tennis, mission college tennis, ultra performance academy, "
            "USTA certified tennis coach"
        ),
        "schemas": [
            {
                "@context": "https://schema.org",
                "@type": ["SportsClub", "LocalBusiness"],
                "name": "Ultra Performance Academy",
                "description": (
                    "Bay Area premier tennis academy in Santa Clara, CA. Expert "
                    "coaching by Stephanie Huang and USTA-certified coaches. "
                    "Private lessons, group clinics, summer camps."
                ),
                "url": SITE_HOME,
                "telephone": "+1-650-308-8355",
                "email": "info@ultraperformanceacademy.com",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "3000 Mission College Boulevard",
                    "addressLocality": "Santa Clara",
                    "addressRegion": "CA",
                    "postalCode": "95054",
                    "addressCountry": "US",
                },
                "geo": {
                    "@type": "GeoCoordinates",
                    "latitude": 37.3885,
                    "longitude": -121.9760,
                },
                "areaServed": [
                    "Santa Clara",
                    "Sunnyvale",
                    "Cupertino",
                    "San Jose",
                    "Mountain View",
                    "Silicon Valley",
                    "Bay Area",
                ],
                "sport": "Tennis",
                "founder": {
                    "@type": "Person",
                    "name": "Stephanie Huang",
                    "jobTitle": "Head Tennis Coach & Founder",
                },
                "sameAs": [
                    "https://www.facebook.com/profile.php?id=61568350623133",
                    CLEAN_INSTAGRAM,
                ],
            }
        ],
        "seo_html": """
<section class="upa-seo-block" data-upa-seo="home" aria-label="About Ultra Performance Academy">
  <div class="upa-seo-inner">
    <h2>Tennis Lessons in Santa Clara &amp; the Bay Area</h2>
    <p>Bay Area's premier tennis academy, based at <strong>Mission College in Santa Clara, CA</strong>. Founded by <strong>Stephanie Huang</strong> — USTA-certified head coach with 15+ years of experience training players of all levels, from beginners to high-performance competitors.</p>
    <p>At Ultra Performance Academy, we are built on a foundation of respect, hard work, and dedication. Founded by Stephanie Huang — a Kinesiology specialist and former Taiwan Junior Top-5 player — our academy provides world-class tennis coaching at Mission College, Santa Clara, serving players across the Bay Area including Sunnyvale, Cupertino, San Jose, and Silicon Valley.</p>
    <p>Our USTA-certified coaching team includes <strong>Stephanie Huang</strong>, <strong>Francis Sargent</strong> (former Stanford assistant coach), <strong>Li Jing</strong> (Chinese national team coach), <strong>Leon Bax</strong> (PhD, WTA/ATP performance coach), and <strong>Rodrigo Perez</strong> — offering private lessons, group clinics, summer camps, and specialized mental and physical fitness programs for all ages and skill levels.</p>
    <h3>Serving the South Bay Area</h3>
    <p>Ultra Performance Academy is conveniently located at Mission College, 3000 Mission College Blvd, Santa Clara, CA 95054 — easily accessible from Sunnyvale, Cupertino, Mountain View, San Jose, Milpitas, and the greater Silicon Valley area. Whether you're looking for tennis lessons near Santa Clara, youth tennis programs in the South Bay, or high-performance training in Silicon Valley, our coaches are here to help you reach your goals.</p>
    <h3>Now Enrolling: 2026 Summer Camp at Gunderson High School, San Jose</h3>
    <p>Our <strong>2026 tennis summer camp</strong> runs <strong>June 1 – July 31, 2026</strong> at <strong>Gunderson High School in San Jose</strong> — 9 weeks of elite junior training. Morning sessions for Green Dot &amp; YB 1 (UTR ≤ 4); afternoon sessions for YB 2 (UTR 4–6.5) and YB 3 (UTR 6.5+). <strong>$140/session</strong> with <strong>10% off</strong> weekly registration. <a href="summerholiday-camp.html#camp-2026">See the full 2026 summer camp details</a>.</p>

    <p class="upa-seo-cta"><a href="contact.html">Book a lesson</a> · <a href="coaches.html">Meet our coaches</a> · <a href="summerholiday-camp.html#camp-2026">2026 Summer Camp</a></p>
  </div>
</section>
""".strip(),
    },
    "coaches.html": {
        "slug": "coaches",
        "title": "Meet Our Coaches — Stephanie Huang & Team | Ultra Performance Academy",
        "description": (
            "Meet the expert coaching team at Ultra Performance Academy in Santa Clara, CA. "
            "Led by founder Stephanie Huang (USTA Certified, WTA Certified, former Taiwan Junior "
            "Top-5), our coaches include Francis Sargent (Stanford/UC Berkeley), Li Jing "
            "(Chinese national team), Leon Bax (PhD, WTA/ATP) and Rodrigo Perez. Bay Area "
            "tennis coaching at its best."
        ),
        "keywords": (
            "Stephanie Huang tennis coach, Francis Sargent tennis, Li Jing tennis coach bay area, "
            "Leon Bax performance coach, USTA certified tennis coach santa clara, "
            "bay area tennis coach, ultra performance academy coaches, tennis instructor silicon valley"
        ),
        "schemas": [
            {
                "@context": "https://schema.org",
                "@type": "Person",
                "name": "Stephanie Huang",
                "jobTitle": "Head Tennis Coach & Founder",
                "worksFor": {
                    "@type": "SportsClub",
                    "name": "Ultra Performance Academy",
                    "url": SITE_HOME,
                },
                "knowsAbout": [
                    "Tennis Coaching",
                    "Kinesiology",
                    "Youth Tennis",
                    "USTA Competition",
                ],
                "hasCredential": [
                    "USTA Certified Professional Coach",
                    "WTA Coach Certification",
                    "USTA Safe Play Approved",
                ],
                "description": (
                    "Founder and Head Coach at Ultra Performance Academy, Santa Clara, CA. "
                    "Former Taiwan Junior Top-5 player, USTA and WTA certified. 15+ years of "
                    "coaching experience at all levels."
                ),
            }
        ],
        "seo_html": """
<section class="upa-seo-block" data-upa-seo="coaches" aria-label="Tennis coaching team">
  <div class="upa-seo-inner">
    <h1>Meet Our Tennis Coaches — Bay Area's Most Experienced Coaching Team</h1>
    <p>The coaching team at Ultra Performance Academy in <strong>Santa Clara, CA</strong> combines elite competitive experience with deep teaching expertise. Every coach below is available for private lessons, group clinics, and summer camp sessions at Mission College.</p>

    <h2>Stephanie Huang — Founder &amp; Head Tennis Coach</h2>
    <p>A former top-5 junior competitor in Taiwan and #1 singles and doubles player for her college team, Stephanie brings elite competitive experience to every lesson. Holding both <strong>USTA Professional Coach</strong> and <strong>WTA Coach</strong> certifications, she specializes in developing junior players for USTA tournament competition across the Bay Area — from beginner foundations to high-performance match preparation. Parents throughout Santa Clara, Sunnyvale, and Cupertino trust Stephanie and the Ultra Performance team to guide their children's tennis development.</p>

    <h3>Francis Sargent — Elite Coach, Former Stanford &amp; UC Berkeley Assistant</h3>
    <p>Former assistant coach at Stanford University and UC Berkeley, Francis brings collegiate-level coaching expertise to high-performance juniors and adults.</p>

    <h3>Li Jing — National-Level Coach, Chinese Women's National Team</h3>
    <p>Former coach for the Chinese women's national team, Li Jing specializes in developing technically sound, tournament-ready players.</p>

    <h3>Leon Bax — Peak Performance &amp; Mental Fitness Coach</h3>
    <p>PhD-trained WTA/ATP performance coach, Leon focuses on the mental and physiological foundations of high-level competitive play.</p>

    <h3>Rodrigo Perez — Development Coach, USTA Development Certified</h3>
    <p>USTA Development Certified, Rodrigo leads junior development programs from beginner Green Dot to early competitive play.</p>

    <p class="upa-seo-cta"><a href="contact.html">Book a session</a> · <a href="programs.html">View programs</a></p>
  </div>
</section>
""".strip(),
    },
    "summerholiday-camp.html": {
        "slug": "summerholiday-camp",
        "title": "Tennis Summer Camp San Jose 2026 — Gunderson High School | Ultra Performance Academy",
        "description": (
            "Ultra Performance Academy 2026 tennis summer camp at Gunderson High School, "
            "San Jose, CA. Nine weeks of elite junior training, June 1 – July 31, 2026. "
            "Morning session for Green Dot & YB 1 (UTR ≤ 4); afternoon session for YB 2 "
            "(UTR 4–6.5) and YB 3 (UTR 6.5+). $140 per session, 10% off weekly. Limited spots."
        ),
        "keywords": (
            "2026 tennis summer camp san jose, gunderson high school tennis camp, "
            "junior tennis camp bay area 2026, UTR tennis camp san jose, "
            "kids tennis summer program silicon valley, ultra performance academy summer camp, "
            "YB tennis training, tennis camp 95136"
        ),
        "og_image": SITE_BASE + "/assets/site/2026-summer-camp-flyer.png",
        "schemas": [
            {
                "@context": "https://schema.org",
                "@type": "Event",
                "name": "Ultra Performance Academy 2026 Tennis Summer Camp",
                "description": (
                    "2026 tennis summer camp at Gunderson High School, San Jose, CA — 9 weeks "
                    "of elite junior training. Morning session for Green Dot & YB 1 (UTR ≤ 4); "
                    "afternoon session for YB 2 (UTR 4–6.5) and YB 3 (UTR 6.5+)."
                ),
                "image": SITE_BASE + "/assets/site/2026-summer-camp-flyer.png",
                "startDate": "2026-06-01",
                "endDate": "2026-07-31",
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                "eventStatus": "https://schema.org/EventScheduled",
                "location": {
                    "@type": "Place",
                    "name": "Gunderson High School",
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "622 Gaundabert Ln",
                        "addressLocality": "San Jose",
                        "addressRegion": "CA",
                        "postalCode": "95136",
                        "addressCountry": "US",
                    },
                },
                "organizer": {
                    "@type": "SportsClub",
                    "name": "Ultra Performance Academy",
                    "url": SITE_HOME,
                    "email": "summer.jiang.up@gmail.com",
                    "telephone": "+1-408-831-0412",
                },
                "offers": {
                    "@type": "Offer",
                    "priceCurrency": "USD",
                    "price": "140",
                    "url": page_url("summerholiday-camp"),
                    "availability": "https://schema.org/LimitedAvailability",
                    "validFrom": "2025-11-01",
                },
            }
        ],
        "seo_html": """
<section id="camp-2026" class="upa-seo-block" data-upa-seo="summer-camp" aria-label="2026 Tennis Summer Camp">
  <div class="upa-seo-inner">
    <h1>2026 Tennis Summer Camp in San Jose — 9 Weeks at Gunderson High School</h1>

    <figure class="upa-camp-flyer">
      <img src="assets/site/2026-summer-camp-flyer.png"
           alt="Ultra Performance Academy 2026 Summer Camp flyer — June 1 through July 31, 2026 at Gunderson High School, San Jose. Morning session 9am–12:30pm for YB 1 and Green Dot, afternoon session 1:30pm–5pm for YB 2 and YB 3. $140 per session, 10% off weekly registration."
           width="900" height="1280"
           loading="eager" decoding="async">
    </figure>

    <p>Train this summer with <strong>Ultra Performance Academy</strong> at <strong>Gunderson High School in San Jose</strong> — <strong>9 weeks of elite junior tennis training from June 1 through July 31, 2026</strong>. Sessions run Monday through Friday with only one day off (July 3). From Green Dot beginners to UTR 6.5+ competitors, our small-group, performance-focused training builds technique, match strategy, and confidence.</p>

    <h2>Camp Schedule &amp; Levels</h2>

    <h3>Morning Session — YB 1 (UTR 4 &amp; below) &amp; Green Dot</h3>
    <p><strong>9:00 AM – 12:30 PM</strong>. Foundational technical training, footwork, point construction, and supervised match play for beginners through developing juniors. Ideal for first-time campers and players building a competitive base.</p>

    <h3>Afternoon Session — YB 2 (UTR 4 – 6.5) &amp; YB 3 (UTR 6.5+)</h3>
    <p><strong>1:30 PM – 5:00 PM</strong>. High-intensity training for tournament-ready and advanced juniors — 3.5 hours of advanced drills, live point play, match strategy, and conditioning. The right environment for players preparing for UTR and USTA competition.</p>

    <h2>Pricing &amp; Weekly Discount</h2>
    <p><strong>$140 per session</strong>. Register for the entire week and receive <strong>10% off</strong> the weekly rate. Quality training only — spots are very limited.</p>

    <h2>What's Included</h2>
    <ul>
      <li>High-quality coaching from Ultra Performance Academy's USTA-certified team</li>
      <li>Skill development across stroke production, footwork, and tactics</li>
      <li>Live match play and point-construction strategy</li>
      <li>Fun, focused, motivating training environment</li>
    </ul>

    <h2>Location</h2>
    <p><strong>Gunderson High School</strong><br>
    622 Gaundabert Ln, San Jose, CA 95136 — easily accessible from Almaden, Willow Glen, Cambrian, and the greater South Bay.</p>

    <h2>Reserve Your Spot</h2>
    <ul class="upa-seo-contact">
      <li><strong>WeChat:</strong> noveltyjx</li>
      <li><strong>Text:</strong> <a href="sms:+14088310412">(408) 831-0412</a></li>
      <li><strong>Email:</strong> <a href="mailto:summer.jiang.up@gmail.com">summer.jiang.up@gmail.com</a></li>
    </ul>

    <p class="upa-seo-cta"><a href="contact.html">Register now</a> · <a href="coaches.html">Meet our coaches</a></p>
  </div>
</section>
""".strip(),
    },
    "group-lessons.html": {
        "slug": "group-lessons",
        "title": "Group Tennis Lessons & Clinics in Santa Clara | Ultra Performance Academy",
        "description": (
            "Join Ultra Performance Academy's group tennis lessons in Santa Clara, CA. "
            "Programs for kids, juniors, and adults — beginner through pre-elite levels "
            "(UTR 6.5+). Saturday clinics, weeknight sessions, adult lessons, and fitness "
            "classes. $40–$100/session at Mission College."
        ),
        "keywords": (
            "group tennis lessons santa clara, kids tennis classes bay area, "
            "junior tennis clinic silicon valley, adult tennis lessons santa clara, "
            "UTR tennis training, tennis fitness class, tennis clinic near me"
        ),
        "schemas": [
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "How much do group tennis lessons cost in Santa Clara?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": (
                                "Group sessions at Ultra Performance Academy range from $40 "
                                "(fitness class, 1 hour) to $100 (Pre-Elite, 2–3 hours). Most "
                                "clinics are $60–$90 per session with limited spots available."
                            ),
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "What age groups do your tennis clinics serve?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": (
                                "We offer programs for players of all ages — from juniors as "
                                "young as 8 years old through adult players. Fitness classes "
                                "are grouped by age: 8–11, 11–15, and 15+."
                            ),
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Do I need a UTR rating to join?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": (
                                "Not necessarily. The Development (Green Dot) and Adult "
                                "programs are open to all levels. For Performance Prep and "
                                "above, a UTR rating helps us place you correctly — but we can "
                                "also conduct an on-court evaluation if you don't have one yet."
                            ),
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Where are group lessons held?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": (
                                "All sessions are held at Mission College, 3000 Mission "
                                "College Blvd, Santa Clara, CA 95054 — easily accessible from "
                                "Sunnyvale, Cupertino, San Jose, and the greater Bay Area."
                            ),
                        },
                    },
                ],
            }
        ],
        "seo_html": """
<section class="upa-seo-block" data-upa-seo="group-lessons" aria-label="Group Tennis Lessons">
  <div class="upa-seo-inner">
    <h1>Group Tennis Lessons in Santa Clara, CA — All Ages &amp; Levels</h1>
    <p>Ultra Performance Academy offers structured <strong>group tennis clinics at Mission College, Santa Clara</strong>, designed for players from beginners to pre-elite competitors. Our small-group format — with limited spots per session — ensures every player receives focused coaching and meaningful improvement. Sessions run on weekday evenings and Saturday mornings, serving players across <strong>Santa Clara, Sunnyvale, Cupertino, and the greater Bay Area</strong>.</p>

    <h3>Development Program — Green Dot</h3>
    <p>Intermediate-level group clinic for players who can rally consistently. 1.5-hour competitive training session on Saturdays, 9:30–11:00am. <strong>$60/session</strong>. Limited spots.</p>

    <h3>Performance Prep Program</h3>
    <p>Competitive training for developing tournament players rated UTR 3.5 and below. 2-hour sessions on Fridays, 5:30–7:30pm. <strong>$80/session</strong>. Evaluation available for players without a UTR rating.</p>

    <h3>High Performance (UTR 3.5–6.5)</h3>
    <p>High-intensity tennis and fitness training for competitive juniors and adults. 2.5-hour sessions on Wednesdays, 5:00–7:30pm. <strong>$90/session</strong>. Includes on-court drills and conditioning work.</p>

    <h3>Pre-Elite Program (UTR 6.5+)</h3>
    <p>Elite-level competitive training for advanced tournament players. 2–3 hour sessions on Wednesdays. <strong>$100/session</strong>. Contact us to confirm eligibility and scheduling.</p>

    <h3>Fitness Class</h3>
    <p>Tennis-specific fitness and conditioning for juniors. Three age-group time slots available: ages 8–11, ages 11–15, and ages 15+. 1-hour session, <strong>$40</strong>. Wednesday evenings at Mission College.</p>

    <h3>Adult Lesson</h3>
    <p>Group adult tennis lessons for all skill levels from complete beginners to NTRP 4.5 players. 2-hour sessions, <strong>$60/session</strong>. Flexible scheduling available — contact us for current times.</p>

    <h2>Frequently Asked Questions</h2>

    <h3>How much do group tennis lessons cost in Santa Clara?</h3>
    <p>Group sessions at Ultra Performance Academy range from $40 (fitness class, 1 hour) to $100 (Pre-Elite, 2–3 hours). Most clinics are $60–$90 per session with limited spots available.</p>

    <h3>What age groups do your tennis clinics serve?</h3>
    <p>We offer programs for players of all ages — from juniors as young as 8 years old through adult players. Fitness classes are grouped by age: 8–11, 11–15, and 15+.</p>

    <h3>Do I need a UTR rating to join?</h3>
    <p>Not necessarily. The Development (Green Dot) and Adult programs are open to all levels. For Performance Prep and above, a UTR rating helps us place you correctly — but we can also conduct an on-court evaluation if you don't have one yet.</p>

    <h3>Where are group lessons held?</h3>
    <p>All sessions are held at Mission College, 3000 Mission College Blvd, Santa Clara, CA 95054 — easily accessible from Sunnyvale, Cupertino, San Jose, and the greater Bay Area.</p>

    <p class="upa-seo-cta"><a href="contact.html">Reserve a spot</a> · <a href="coaches.html">Meet our coaches</a></p>
  </div>
</section>
""".strip(),
    },
    "programs.html": {
        "slug": "programs",
        "title": "Tennis Programs in Santa Clara — Private, Group & Fitness | Ultra Performance Academy",
        "description": (
            "Explore Ultra Performance Academy's tennis programs in Santa Clara, CA: private "
            "one-on-one lessons, group clinics, summer camps, mental fitness coaching, and "
            "physical conditioning. USTA-certified coaches. All ages and skill levels welcome. "
            "Serving the Bay Area."
        ),
        "keywords": (
            "private tennis lessons bay area, tennis programs santa clara, "
            "group tennis clinics silicon valley, tennis mental fitness training, "
            "tennis physical conditioning, USTA tennis lessons, tennis academy programs"
        ),
        "schemas": [],
        "seo_html": """
<section class="upa-seo-block" data-upa-seo="programs" aria-label="Tennis Programs">
  <div class="upa-seo-inner">
    <h1>Tennis Training Programs in Santa Clara, CA</h1>
    <p>Ultra Performance Academy offers a full ladder of tennis programs at <strong>Mission College in Santa Clara</strong> — from first-racket beginners to advanced tournament players. All programs are run by our USTA-certified coaching team led by <strong>Stephanie Huang</strong>.</p>

    <h3>Group Tennis Lessons</h3>
    <p>Our group tennis clinics in Santa Clara bring together players of similar levels for structured, high-energy training sessions. Perfect for juniors and adults who want to improve technique, build match experience, and train alongside motivated peers — at a cost-effective rate.</p>

    <h3>Private Tennis Lessons</h3>
    <p>One-on-one private lessons with our USTA-certified coaches are the fastest way to improve your game. Sessions are fully tailored to your strengths, weaknesses, and goals — whether you're a beginner picking up a racket for the first time or a competitive junior preparing for USTA tournaments.</p>

    <h3>Summer &amp; Holiday Camps</h3>
    <p>Our flagship <strong>2026 Summer Camp at Gunderson High School in San Jose</strong> runs <strong>June 1 – July 31, 2026</strong> — 9 weeks of intensive training for juniors from Green Dot beginners up to UTR 6.5+ tournament players. Morning and afternoon sessions, daily technical drills, match play, and strategy work. <strong>$140/session</strong>, 10% off weekly registration. Holiday camps run year-round on school breaks.</p>

    <h3>Specialized Physical Fitness</h3>
    <p>Tennis-specific strength, agility, and conditioning training designed to make you faster, stronger, and more explosive on the court. Programs are available for juniors (ages 8+) and adults, targeting footwork, core stability, endurance, and injury prevention.</p>

    <p class="upa-seo-cta"><a href="contact.html">Book a program</a> · <a href="group-lessons.html">View group lessons</a> · <a href="summerholiday-camp.html#camp-2026">2026 Summer Camp</a></p>
  </div>
</section>
""".strip(),
    },
    "contact.html": {
        "slug": "contact",
        "title": "Contact Us — Book a Tennis Lesson in Santa Clara | Ultra Performance Academy",
        "description": (
            "Contact Ultra Performance Academy to book tennis lessons, group clinics, or "
            "summer camp sessions in Santa Clara, CA. Located at Mission College. Call "
            "(650) 308-8355 or email info@ultraperformanceacademy.com. Serving the "
            "Bay Area."
        ),
        "keywords": (
            "contact ultra performance academy, book tennis lesson santa clara, "
            "tennis lesson bay area, mission college tennis contact, tennis academy phone"
        ),
        "schemas": [
            {
                "@context": "https://schema.org",
                "@type": "LocalBusiness",
                "name": "Ultra Performance Academy",
                "url": SITE_HOME,
                "telephone": "+1-650-308-8355",
                "email": "info@ultraperformanceacademy.com",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "3000 Mission College Boulevard",
                    "addressLocality": "Santa Clara",
                    "addressRegion": "CA",
                    "postalCode": "95054",
                    "addressCountry": "US",
                },
            }
        ],
        "seo_html": """
<section class="upa-seo-block" data-upa-seo="contact" aria-label="Contact Ultra Performance Academy">
  <div class="upa-seo-inner">
    <h1>Contact Ultra Performance Academy — Tennis Lessons in Santa Clara</h1>
    <p>Ready to start your tennis journey? Whether you're looking for private lessons, group clinics, summer camps, or have questions about our programs, our team is happy to help.</p>
    <p>Ultra Performance Academy is located at <strong>Mission College in Santa Clara, CA</strong> — easily accessible from Sunnyvale, Cupertino, San Jose, Mountain View, and the greater South Bay Area.</p>
    <ul class="upa-seo-contact">
      <li><strong>Phone:</strong> <a href="tel:+16503088355">(650) 308-8355</a></li>
      <li><strong>Email:</strong> <a href="mailto:info@ultraperformanceacademy.com">info@ultraperformanceacademy.com</a> or <a href="mailto:summer.jiang.up@gmail.com">summer.jiang.up@gmail.com</a></li>
      <li><strong>Address:</strong> 3000 Mission College Boulevard, Santa Clara, CA 95054</li>
      <li><strong>Instagram:</strong> <a href="https://www.instagram.com/ultra.performance.academy" rel="noopener" target="_blank">@ultra.performance.academy</a></li>
    </ul>
  </div>
</section>
""".strip(),
    },
    "small-group.html": {
        "slug": "small-group",
        "title": "Small Group Tennis Coaching in Santa Clara | Ultra Performance Academy",
        "description": (
            "Small-group tennis coaching at Ultra Performance Academy in Santa Clara, CA. "
            "Personalized attention with 2–4 players per coach. Held at Mission College. "
            "Bay Area's premier junior and adult tennis training."
        ),
        "keywords": (
            "small group tennis lessons santa clara, semi-private tennis bay area, "
            "tennis training silicon valley, junior tennis coaching, mission college tennis"
        ),
        "schemas": [],
        "seo_html": """
<section class="upa-seo-block" data-upa-seo="small-group" aria-label="Small-group tennis coaching">
  <div class="upa-seo-inner">
    <h1>Small-Group Tennis Coaching in Santa Clara, CA</h1>
    <p>Train in a focused, semi-private setting with just 2–4 players per coach at <strong>Mission College in Santa Clara</strong>. Small-group coaching at Ultra Performance Academy gives you the depth of attention of private lessons at a fraction of the cost — ideal for juniors and adults serious about technical improvement.</p>
    <p>All sessions are led by our USTA-certified team, including <strong>Stephanie Huang</strong>, serving players across Santa Clara, Sunnyvale, Cupertino, and the greater Bay Area.</p>
    <p class="upa-seo-cta"><a href="contact.html">Book a small-group session</a> · <a href="coaches.html">Meet our coaches</a></p>
  </div>
</section>
""".strip(),
    },
}


# ---------------------------------------------------------------------------
# Patch helpers
# ---------------------------------------------------------------------------

def _replace_title(html: str, new_title: str) -> str:
    return re.sub(
        r"<title>[^<]*</title>",
        f"<title>{html_lib.escape(new_title)}</title>",
        html,
        count=1,
    )


def _replace_meta(html: str, name: str, value: str) -> str:
    attr = html_lib.escape(value, quote=True)
    pattern = re.compile(
        rf'<meta\s+name="{re.escape(name)}"\s+content="[^"]*"\s*/?>',
        re.IGNORECASE,
    )
    replacement = f'<meta name="{name}" content="{attr}">'
    if pattern.search(html):
        return pattern.sub(replacement, html, count=1)
    return html.replace("</title>", f"</title>{replacement}", 1)


def _replace_meta_prop(html: str, prop: str, value: str) -> str:
    """Replace a <meta property="og:..."> tag, regardless of attribute order."""
    attr = html_lib.escape(value, quote=True)
    target = f'<meta content="{attr}" property="{prop}">'
    pattern = re.compile(
        rf'<meta\s+[^>]*property="{re.escape(prop)}"[^>]*>',
        re.IGNORECASE,
    )
    if pattern.search(html):
        return pattern.sub(target, html, count=1)
    return html.replace("</head>", f"{target}</head>", 1)


def _replace_meta_named(html: str, name: str, value: str) -> str:
    """Replace a <meta name="twitter:..."> tag, regardless of attribute order."""
    attr = html_lib.escape(value, quote=True)
    target = f'<meta name="{name}" content="{attr}">'
    pattern = re.compile(
        rf'<meta\s+[^>]*name="{re.escape(name)}"[^>]*>',
        re.IGNORECASE,
    )
    if pattern.search(html):
        return pattern.sub(target, html, count=1)
    return html.replace("</head>", f"{target}</head>", 1)


def _update_social_cards(html: str, cfg: dict) -> str:
    url = page_url(cfg["slug"])
    title = cfg["title"]
    desc = cfg["description"]
    image = cfg.get("og_image") or DEFAULT_OG_IMAGE
    html = _replace_meta_prop(html, "og:url", url)
    html = _replace_meta_prop(html, "og:title", title)
    html = _replace_meta_prop(html, "og:description", desc)
    html = _replace_meta_prop(html, "og:site_name", "Ultra Performance Academy")
    html = _replace_meta_prop(html, "og:type", "website")
    html = _replace_meta_prop(html, "og:image", image)
    html = _replace_meta_named(html, "twitter:image", image)
    html = _replace_meta_named(html, "twitter:title", title)
    html = _replace_meta_named(html, "twitter:description", desc)
    html = _replace_meta_named(html, "twitter:card", "summary_large_image")
    return html


def _strip_existing_seo_blocks(html: str) -> str:
    """Remove previously injected SEO content (idempotency) AND the stub WebSite
    JSON-LD that Hostinger ships with — keeping multiple conflicting JSON-LD
    blocks confuses Google.
    """
    html = re.sub(
        r'<script type="application/ld\+json"[^>]*>.*?</script>',
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<section\b[^>]*\bclass="[^"]*\bupa-seo-block\b[^"]*"[^>]*\bdata-upa-seo="[^"]*"[^>]*>.*?</section>',
        "",
        html,
        flags=re.DOTALL,
    )
    return html


def _inject_jsonld(html: str, slug: str, schemas: list[dict]) -> str:
    if not schemas:
        return html
    parts = []
    for i, s in enumerate(schemas):
        sid = f"{slug}-{i}"
        body = json.dumps(s, separators=(",", ":"), ensure_ascii=False)
        parts.append(
            f'<script type="application/ld+json" {SENTINEL}="{sid}">{body}</script>'
        )
    blob = "".join(parts)
    return html.replace("</head>", f"{blob}</head>", 1)


_FOOTER_SECTION_RE = re.compile(
    r'<section\b[^>]*class="[^"]*\bblock--footer\b[^"]*"[^>]*>',
    re.IGNORECASE,
)


def _inject_seo_section(html: str, seo_html: str) -> str:
    """Inject the SEO content block right ABOVE the Hostinger footer block.

    Hostinger emits the footer as `<section class="block block--footer">…</section>`
    inside `<main>`. To keep the visible footer at the bottom, we insert our
    block just before that opening tag. Fallbacks: `</main>` then `</body>`.
    """
    if not seo_html:
        return html
    m = _FOOTER_SECTION_RE.search(html)
    if m:
        return html[: m.start()] + seo_html + html[m.start() :]
    if "</main>" in html:
        return html.replace("</main>", f"{seo_html}</main>", 1)
    return html.replace("</body>", f"{seo_html}</body>", 1)


def _clean_links(html: str) -> str:
    """Clean tracking params on safe surfaces only.

    Important: we MUST NOT regex over `<astro-island props="...">` JSON, because
    that JSON uses HTML-encoded `&quot;` quotes — a naive `[^"]*` would consume
    across field boundaries and corrupt the props (and break client hydration).
    So we target only:
      * `href="..."` attributes  (boundary is a literal `"`)
      * Visible `>text<` between tags  (boundary is `>` and `<`)

    Note: we deliberately keep `summer.jiang.up@gmail.com` — the site's
    secondary contact email — intact everywhere it appears.
    """
    html = re.sub(
        r'href="https://www\.instagram\.com/ultra\.performance\.academy\?[^"]*"',
        f'href="{CLEAN_INSTAGRAM}"',
        html,
    )
    return html


# ---------------------------------------------------------------------------
# Task 08 — image alt text inside the Astro hydration props
# ---------------------------------------------------------------------------

COACH_ALT = {
    "stephanie": "Stephanie Huang, founder and head tennis coach at Ultra Performance Academy, Santa Clara CA",
    "huang": "Stephanie Huang, founder and head tennis coach at Ultra Performance Academy, Santa Clara CA",
    "francis": "Francis Sargent, elite tennis coach at Ultra Performance Academy, former Stanford University assistant coach",
    "sargent": "Francis Sargent, elite tennis coach at Ultra Performance Academy, former Stanford University assistant coach",
    "li-jing": "Li Jing, tennis coach at Ultra Performance Academy, former Chinese national team coach",
    "lijing": "Li Jing, tennis coach at Ultra Performance Academy, former Chinese national team coach",
    "leon": "Leon Bax, peak performance and mental fitness tennis coach at Ultra Performance Academy",
    "bax": "Leon Bax, peak performance and mental fitness tennis coach at Ultra Performance Academy",
    "rodrigo": "Rodrigo Perez, USTA development tennis coach at Ultra Performance Academy Santa Clara",
    "perez": "Rodrigo Perez, USTA development tennis coach at Ultra Performance Academy Santa Clara",
}

GENERIC_ALT_BY_SLUG = {
    "home": [
        "Tennis training session at Mission College Santa Clara",
        "Junior tennis players during group clinic at Ultra Performance Academy",
        "Tennis coaching drill at Ultra Performance Academy Bay Area",
        "Court action at Ultra Performance Academy Santa Clara",
    ],
    "coaches": [
        "Coaching session at Ultra Performance Academy Santa Clara",
        "Tennis instruction at Mission College Santa Clara",
    ],
    "summerholiday-camp": [
        "Kids tennis summer camp at Mission College Santa Clara 2025",
        "Junior players during summer tennis camp drills at Ultra Performance Academy",
        "Tennis summer camp match play session at Ultra Performance Academy Bay Area",
        "Summer tennis clinic at Mission College Santa Clara",
    ],
    "group-lessons": [
        "Group tennis clinic at Mission College Santa Clara",
        "Junior tennis players during Saturday group lesson at Ultra Performance Academy",
        "Tennis fitness training session for juniors at Ultra Performance Academy",
        "Adult tennis lesson at Mission College Santa Clara",
    ],
    "programs": [
        "Private tennis lesson at Mission College Santa Clara",
        "Group tennis clinic at Ultra Performance Academy Santa Clara",
        "Junior summer tennis camp at Ultra Performance Academy Bay Area",
        "Tennis fitness conditioning training at Ultra Performance Academy",
    ],
    "contact": [
        "Ultra Performance Academy tennis training at Mission College Santa Clara",
    ],
    "small-group": [
        "Small-group tennis coaching at Mission College Santa Clara",
        "Semi-private tennis training at Ultra Performance Academy",
    ],
}

DEFAULT_GENERIC = [
    "Tennis training at Ultra Performance Academy, Mission College Santa Clara",
    "Tennis coaching session at Ultra Performance Academy Bay Area",
]


def _alt_for_path(path: str, slug: str, counter: list[int]) -> str:
    lower = path.lower()
    for key, alt in COACH_ALT.items():
        if key in lower:
            return alt
    pool = GENERIC_ALT_BY_SLUG.get(slug) or DEFAULT_GENERIC
    alt = pool[counter[0] % len(pool)]
    counter[0] += 1
    return alt


def _v(x):
    """Unwrap a single [N, value] Astro hydration pair."""
    if isinstance(x, list) and len(x) == 2 and isinstance(x[0], int):
        return x[1]
    return x


def _patch_alt_in_tree(obj, slug: str, counter: list[int]) -> None:
    if isinstance(obj, dict):
        typ = _v(obj.get("type"))
        if typ == "GridImage":
            settings = _v(obj.get("settings"))
            if isinstance(settings, dict):
                path_str = _v(settings.get("path"))
                alt_wrapper = settings.get("alt")
                current_alt = _v(alt_wrapper) if alt_wrapper else ""
                if not current_alt and isinstance(path_str, str) and path_str:
                    new_alt = _alt_for_path(path_str, slug, counter)
                    if isinstance(alt_wrapper, list) and len(alt_wrapper) == 2:
                        alt_wrapper[1] = new_alt
                    else:
                        settings["alt"] = [0, new_alt]
        elif typ == "GridGallery":
            images = _v(obj.get("images"))
            if isinstance(images, list):
                for im_wrapper in images:
                    im = _v(im_wrapper)
                    if not isinstance(im, dict):
                        continue
                    path_str = _v(im.get("path"))
                    alt_wrapper = im.get("alt")
                    current_alt = _v(alt_wrapper) if alt_wrapper else ""
                    if not current_alt and isinstance(path_str, str) and path_str:
                        new_alt = _alt_for_path(path_str, slug, counter)
                        if isinstance(alt_wrapper, list) and len(alt_wrapper) == 2:
                            alt_wrapper[1] = new_alt
                        else:
                            im["alt"] = [0, new_alt]
        for v in obj.values():
            _patch_alt_in_tree(v, slug, counter)
    elif isinstance(obj, list):
        for v in obj:
            _patch_alt_in_tree(v, slug, counter)


def _clean_string_value(s: str) -> str:
    """Clean Instagram tracking inside a string value (used for strings stored
    INSIDE the Astro hydration JSON props).

    Note: `summer.jiang.up@gmail.com` is intentionally preserved — it's a real
    secondary contact email displayed in the footer.
    """
    if not isinstance(s, str):
        return s
    if "igsh=" in s or "utm_source=qr" in s:
        s = re.sub(
            r"https://www\.instagram\.com/ultra\.performance\.academy\?[^\s<>\"']*",
            CLEAN_INSTAGRAM,
            s,
        )
    return s


def _clean_strings_in_tree(obj) -> int:
    """Walk a parsed JSON tree, replace dirty string values in place.
    Returns number of replacements."""
    n = 0
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, str):
                cleaned = _clean_string_value(v)
                if cleaned != v:
                    obj[k] = cleaned
                    n += 1
            else:
                n += _clean_strings_in_tree(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                cleaned = _clean_string_value(v)
                if cleaned != v:
                    obj[i] = cleaned
                    n += 1
            else:
                n += _clean_strings_in_tree(v)
    return n


def _patch_island_alts(html: str, slug: str) -> tuple[str, int, int]:
    """Locate the Astro Page island, decode its props, fill missing alt text
    AND clean dirty strings (Instagram tracking, Gmail), re-encode and write
    back into the HTML.

    Returns (new_html, alts_filled, strings_cleaned).
    """
    idx = html.find('component-url="assets/astro/Page.')
    if idx == -1:
        return html, 0, 0
    start = html.rfind("<astro-island", 0, idx)
    end = html.find("></astro-island>", idx)
    if start < 0 or end < 0:
        return html, 0, 0
    chunk = html[start : end + len("></astro-island>")]

    ps = chunk.find('props="')
    if ps < 0:
        return html, 0, 0
    attr_start = ps + len('props="')
    # Robust end-of-props detection: walk forward looking for the first literal
    # `"` whose next char is whitespace or `>` (attribute boundary).
    p = attr_start
    props_end = None
    while True:
        q = chunk.find('"', p)
        if q < 0:
            break
        nxt = chunk[q + 1 : q + 2]
        if nxt in (" ", "\t", "\n", ">", "/"):
            props_end = q
            break
        p = q + 1
    if props_end is None:
        return html, 0, 0

    encoded = chunk[attr_start:props_end]
    decoded = html_lib.unescape(encoded)
    try:
        data = json.loads(decoded)
    except json.JSONDecodeError:
        return html, 0, 0

    counter = [0]
    _patch_alt_in_tree(data, slug, counter)
    cleaned = _clean_strings_in_tree(data)
    if counter[0] == 0 and cleaned == 0:
        return html, 0, 0

    new_decoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    new_encoded = html_lib.escape(new_decoded, quote=True)
    new_chunk = chunk[:attr_start] + new_encoded + chunk[props_end:]
    new_html = html[:start] + new_chunk + html[end + len("></astro-island>") :]
    return new_html, counter[0], cleaned


def _ensure_canonical(html: str, slug: str) -> str:
    tag = f'<link rel="canonical" href="{page_url(slug)}">'
    pattern = re.compile(r'<link[^>]+rel="canonical"[^>]*>', re.IGNORECASE)
    if pattern.search(html):
        return pattern.sub(tag, html, count=1)
    return html.replace("</head>", f"{tag}</head>", 1)


_SUMMER_SPLASH_RE = re.compile(
    r"<!--\s*upa-summer-splash\s*-->.*?<!--\s*/upa-summer-splash\s*-->\s*",
    re.DOTALL | re.IGNORECASE,
)


def _strip_summer_splash(html: str) -> str:
    return _SUMMER_SPLASH_RE.sub("", html)


def _inject_summer_splash(html: str) -> str:
    return html.replace("</body>", SUMMER_SPLASH_HTML + "\n</body>", 1)


_FAVICON_BLOCK_RE = re.compile(
    r"<!--\s*upa-favicon\s*-->.*?<!--\s*/upa-favicon\s*-->\s*",
    re.DOTALL | re.IGNORECASE,
)


def _strip_favicon_tags(html: str) -> str:
    """Remove prior favicon injection and Hostinger `data:` stub PNG favicons."""
    html = _FAVICON_BLOCK_RE.sub("", html)
    html = re.sub(
        r'<link\s+rel="icon"\s+size="[^"]*"\s+href="data:[^"]*"\s*/?>',
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<link\s+rel="apple-touch-icon"\s+href="data:[^"]*"\s*/?>',
        "",
        html,
        flags=re.IGNORECASE,
    )
    return html


def _inject_favicon(html: str) -> str:
    if "</title>" not in html:
        return html
    return html.replace("</title>", f"</title>\n{FAVICON_HTML}", 1)


def _strip_hostinger_traces(html: str) -> str:
    """Remove tags that identify Hostinger as the site generator."""
    html = re.sub(
        r'<meta\s+name="generator"\s+content="Hostinger[^"]*"\s*/?>',
        "",
        html,
        flags=re.IGNORECASE,
    )
    return html


def _ensure_local_stylesheet(html: str) -> str:
    """Add <link rel="stylesheet" href="css/styles.css"> if not already present.

    Without this, our injected .upa-seo-block has no styling — Hostinger's
    Astro bundle only ships CSS for the components it renders.
    """
    if 'href="css/styles.css"' in html:
        return html
    tag = '<link rel="stylesheet" href="css/styles.css">'
    return html.replace("</head>", f"{tag}</head>", 1)


def patch(path: Path, cfg: dict) -> dict:
    html = path.read_text(encoding="utf-8")
    before_len = len(html)

    html = _strip_existing_seo_blocks(html)
    html = _strip_summer_splash(html)
    html = _strip_hostinger_traces(html)
    html = _strip_favicon_tags(html)
    html = _ensure_local_stylesheet(html)
    html = _replace_title(html, cfg["title"])
    html = _inject_favicon(html)
    html = _replace_meta(html, "description", cfg["description"])
    html = _replace_meta(html, "keywords", cfg["keywords"])
    html = _update_social_cards(html, cfg)
    html = _ensure_canonical(html, cfg["slug"])
    html = _inject_jsonld(html, cfg["slug"], cfg.get("schemas") or [])
    html = _inject_seo_section(html, cfg.get("seo_html") or "")
    html, alt_filled, strings_cleaned = _patch_island_alts(html, cfg["slug"])
    html = _clean_links(html)
    html = _inject_summer_splash(html)

    path.write_text(html, encoding="utf-8")
    return {
        "file": path.name,
        "delta_bytes": len(html) - before_len,
        "alts_filled": alt_filled,
        "json_strings_cleaned": strings_cleaned,
    }


def apply_all(root: Path = ROOT) -> list[dict]:
    out = []
    for fname, cfg in PAGES.items():
        p = root / fname
        if not p.exists():
            print(f"skip {fname} (missing)")
            continue
        info = patch(p, cfg)
        out.append(info)
        print(
            f"patched {info['file']:<28}  "
            f"Δ{info['delta_bytes']:+d} bytes  "
            f"alts={info['alts_filled']}  "
            f"cleaned={info['json_strings_cleaned']}"
        )
    return out


def main() -> int:
    apply_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
