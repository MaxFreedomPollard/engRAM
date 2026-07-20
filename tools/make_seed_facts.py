"""ONE-TIME bootstrap generator for tools/seed/core_facts.jsonl.

After the first run, tools/seed/core_facts.jsonl is the CANONICAL file:
append new facts to it directly (new sequential ids, at the end) and
rebuild with tools/build_seed_pack.py. Re-running this script would
regenerate the file from the hardcoded lists below and destroy any
hand-added facts — so it refuses to overwrite unless given --force.
"""
import json
import pathlib
import sys

CAPITALS = [
    ("France", "Paris"), ("Germany", "Berlin"), ("Italy", "Rome"),
    ("Spain", "Madrid"), ("Portugal", "Lisbon"), ("United Kingdom", "London"),
    ("Ireland", "Dublin"), ("Netherlands", "Amsterdam"), ("Belgium", "Brussels"),
    ("Switzerland", "Bern"), ("Austria", "Vienna"), ("Poland", "Warsaw"),
    ("Czech Republic", "Prague"), ("Greece", "Athens"), ("Norway", "Oslo"),
    ("Sweden", "Stockholm"), ("Finland", "Helsinki"), ("Denmark", "Copenhagen"),
    ("Iceland", "Reykjavik"), ("Russia", "Moscow"), ("Ukraine", "Kyiv"),
    ("Turkey", "Ankara"), ("Egypt", "Cairo"), ("South Africa", "Pretoria"),
    ("Nigeria", "Abuja"), ("Kenya", "Nairobi"), ("Morocco", "Rabat"),
    ("Ethiopia", "Addis Ababa"), ("China", "Beijing"), ("Japan", "Tokyo"),
    ("South Korea", "Seoul"), ("India", "New Delhi"), ("Pakistan", "Islamabad"),
    ("Thailand", "Bangkok"), ("Vietnam", "Hanoi"), ("Indonesia", "Jakarta"),
    ("Philippines", "Manila"), ("Malaysia", "Kuala Lumpur"),
    ("Saudi Arabia", "Riyadh"), ("Israel", "Jerusalem"), ("Iran", "Tehran"),
    ("Iraq", "Baghdad"), ("Australia", "Canberra"), ("New Zealand", "Wellington"),
    ("Canada", "Ottawa"), ("United States", "Washington, D.C."),
    ("Mexico", "Mexico City"), ("Brazil", "Brasília"), ("Argentina", "Buenos Aires"),
    ("Chile", "Santiago"), ("Peru", "Lima"), ("Colombia", "Bogotá"),
    ("Venezuela", "Caracas"), ("Cuba", "Havana"), ("Hungary", "Budapest"),
    ("Romania", "Bucharest"), ("Bulgaria", "Sofia"), ("Croatia", "Zagreb"),
    ("Serbia", "Belgrade"), ("Slovakia", "Bratislava"),
]

ELEMENTS = [
    ("hydrogen", "H", 1), ("helium", "He", 2), ("lithium", "Li", 3),
    ("beryllium", "Be", 4), ("boron", "B", 5), ("carbon", "C", 6),
    ("nitrogen", "N", 7), ("oxygen", "O", 8), ("fluorine", "F", 9),
    ("neon", "Ne", 10), ("sodium", "Na", 11), ("magnesium", "Mg", 12),
    ("aluminium", "Al", 13), ("silicon", "Si", 14), ("phosphorus", "P", 15),
    ("sulfur", "S", 16), ("chlorine", "Cl", 17), ("argon", "Ar", 18),
    ("potassium", "K", 19), ("calcium", "Ca", 20), ("iron", "Fe", 26),
    ("copper", "Cu", 29), ("zinc", "Zn", 30), ("silver", "Ag", 47),
    ("tin", "Sn", 50), ("iodine", "I", 53), ("gold", "Au", 79),
    ("mercury", "Hg", 80), ("lead", "Pb", 82), ("uranium", "U", 92),
]

CONVERSIONS = [
    "One kilometer equals 1000 meters.",
    "One meter equals 100 centimeters.",
    "One inch equals 2.54 centimeters.",
    "One foot equals 12 inches.",
    "One yard equals 3 feet.",
    "One mile equals 5280 feet, or about 1.609 kilometers.",
    "One kilogram equals 1000 grams, or about 2.205 pounds.",
    "One pound equals 16 ounces, or about 453.6 grams.",
    "One metric tonne equals 1000 kilograms.",
    "One liter equals 1000 milliliters.",
    "One US gallon equals about 3.785 liters.",
    "One hour equals 60 minutes, and one minute equals 60 seconds.",
    "One day equals 24 hours, or 1440 minutes.",
    "One week equals 7 days, and a common year has 365 days.",
    "A leap year has 366 days, with February 29 as the extra day.",
    "Water freezes at 0 degrees Celsius, which is 32 degrees Fahrenheit.",
    "Water boils at 100 degrees Celsius at sea level, which is 212 degrees Fahrenheit.",
    "To convert Celsius to Fahrenheit, multiply by 9/5 and add 32.",
    "Zero degrees Kelvin (absolute zero) equals -273.15 degrees Celsius.",
    "One byte equals 8 bits.",
    "One kibibyte equals 1024 bytes; one kilobyte equals 1000 bytes.",
    "One dozen equals 12 items; one gross equals 144 items.",
    "One acre equals 43,560 square feet.",
    "One hectare equals 10,000 square meters.",
    "One nautical mile equals 1.852 kilometers.",
    "One horsepower equals about 746 watts.",
    "One calorie equals about 4.184 joules.",
    "One light-year is about 9.46 trillion kilometers.",
    "One astronomical unit is the average Earth-Sun distance, about 150 million kilometers.",
    "Speed of sound in air at sea level is about 343 meters per second.",
]

DATES = [
    "World War I began in 1914 and ended in 1918.",
    "World War II began in 1939 and ended in 1945.",
    "The United States Declaration of Independence was signed in 1776.",
    "The French Revolution began in 1789.",
    "The Berlin Wall fell in 1989.",
    "The first Moon landing, Apollo 11, was in July 1969.",
    "The Wright brothers made the first powered airplane flight in 1903.",
    "The Titanic sank in April 1912.",
    "The printing press was developed by Johannes Gutenberg around 1440.",
    "Christopher Columbus reached the Americas in 1492.",
    "The Magna Carta was sealed in 1215.",
    "The Roman Empire in the West fell in 476 CE.",
    "The Great Fire of London occurred in 1666.",
    "The United Nations was founded in 1945.",
    "The European Union's euro currency entered circulation in 2002.",
    "The Soviet Union dissolved in 1991.",
    "The first transatlantic telegraph cable was completed in 1858.",
    "Penicillin was discovered by Alexander Fleming in 1928.",
    "The structure of DNA was described by Watson and Crick in 1953.",
    "The World Wide Web was proposed by Tim Berners-Lee in 1989.",
    "The first iPhone was released in 2007.",
    "The Chernobyl nuclear accident occurred in 1986.",
    "The Suez Canal opened in 1869.",
    "The Panama Canal opened in 1914.",
    "The Eiffel Tower was completed in 1889.",
    "The Great Wall of China was largely built during the Ming dynasty (1368-1644).",
    "The Gregorian calendar was introduced in 1582.",
    "Slavery was abolished in the United States by the 13th Amendment in 1865.",
    "Women gained the right to vote in the United States in 1920.",
    "The Universal Declaration of Human Rights was adopted in 1948.",
]

SCIENCE = [
    "Light travels at about 299,792 kilometers per second in a vacuum.",
    "The Earth orbits the Sun once every 365.25 days.",
    "The Earth rotates on its axis once every 24 hours, causing day and night.",
    "The Moon orbits the Earth roughly every 27.3 days.",
    "Gravity on Earth accelerates falling objects at about 9.8 meters per second squared.",
    "Water is made of two hydrogen atoms and one oxygen atom, H2O.",
    "Table salt is sodium chloride, NaCl.",
    "The human body is roughly 60 percent water.",
    "The adult human body has 206 bones.",
    "The human heart has four chambers: two atria and two ventricles.",
    "Normal human body temperature is about 37 degrees Celsius (98.6 Fahrenheit).",
    "Adult humans have 32 teeth including wisdom teeth.",
    "Red blood cells carry oxygen using the protein hemoglobin.",
    "The brain and spinal cord make up the central nervous system.",
    "Neurons transmit signals using electrical impulses and chemical neurotransmitters.",
    "DNA stands for deoxyribonucleic acid and carries genetic information.",
    "Humans normally have 23 pairs of chromosomes, 46 in total.",
    "Photosynthesis converts carbon dioxide and water into glucose and oxygen using sunlight.",
    "Plants absorb carbon dioxide and release oxygen.",
    "Sound cannot travel through a vacuum; it needs a medium.",
    "Atoms consist of protons, neutrons, and electrons.",
    "The atomic nucleus contains protons and neutrons and holds nearly all of an atom's mass.",
    "Protons carry positive charge, electrons negative, neutrons no charge.",
    "The periodic table currently has 118 confirmed elements.",
    "Diamond and graphite are both made purely of carbon.",
    "The most abundant gas in Earth's atmosphere is nitrogen, about 78 percent.",
    "Oxygen makes up about 21 percent of Earth's atmosphere.",
    "The pH scale runs from 0 to 14, with 7 being neutral.",
    "Absolute zero is the lowest possible temperature, where molecular motion is minimal.",
    "Energy cannot be created or destroyed, only transformed (conservation of energy).",
    "The mitochondrion is the organelle that produces most of a cell's ATP energy.",
    "Antibiotics treat bacterial infections, not viral ones.",
    "Vaccines train the immune system to recognize pathogens.",
    "The four classical states of matter are solid, liquid, gas, and plasma.",
    "Copper and silver are excellent electrical conductors.",
    "An electric current is a flow of electric charge, measured in amperes.",
    "Voltage is measured in volts, resistance in ohms, power in watts.",
    "Ohm's law states that voltage equals current times resistance.",
    "The speed of a wave equals its frequency times its wavelength.",
    "Isaac Newton formulated the three laws of motion.",
]

GEOGRAPHY = [
    "The Pacific Ocean is the largest and deepest ocean on Earth.",
    "The Atlantic Ocean is the second-largest ocean.",
    "The Nile and the Amazon are the two longest rivers in the world.",
    "Mount Everest, at 8,849 meters, is Earth's highest mountain above sea level.",
    "The Mariana Trench contains the deepest known point in the ocean.",
    "The Sahara is the largest hot desert in the world.",
    "Antarctica is the coldest continent and holds most of Earth's fresh water as ice.",
    "Africa is the second-largest continent by land area, after Asia.",
    "Australia is both a country and a continent.",
    "The equator divides the Earth into Northern and Southern Hemispheres.",
    "The Amazon rainforest is the largest tropical rainforest on Earth.",
    "The Great Barrier Reef, off Australia, is the world's largest coral reef system.",
    "Russia is the largest country in the world by land area.",
    "Canada has the longest coastline of any country.",
    "The Caspian Sea is the largest inland body of water.",
    "Lake Baikal in Siberia is the deepest freshwater lake.",
    "The Dead Sea shore is the lowest land elevation on Earth.",
    "Greenland is the world's largest island that is not a continent.",
    "The Himalayas contain most of the world's highest peaks.",
    "The Andes is the longest continental mountain range, running along South America.",
    "The Mississippi River flows into the Gulf of Mexico.",
    "The Danube flows through more countries than any other river.",
    "Tokyo is among the most populous metropolitan areas in the world.",
    "The Strait of Gibraltar separates Europe from Africa.",
    "The Panama Canal connects the Atlantic and Pacific Oceans.",
    "The Suez Canal connects the Mediterranean Sea and the Red Sea.",
    "Earth's surface is about 71 percent water.",
    "There are seven continents on Earth.",
    "The Ring of Fire around the Pacific has most of Earth's active volcanoes.",
    "The Gobi Desert spans northern China and southern Mongolia.",
]

MATH = [
    "Pi is approximately 3.14159 and is the ratio of a circle's circumference to its diameter.",
    "The square root of 144 is 12.",
    "A right angle measures 90 degrees.",
    "The angles of a triangle sum to 180 degrees.",
    "The Pythagorean theorem states a squared plus b squared equals c squared for right triangles.",
    "A prime number has exactly two divisors: 1 and itself.",
    "The first five prime numbers are 2, 3, 5, 7, and 11.",
    "Zero is neither positive nor negative.",
    "Any number multiplied by zero equals zero.",
    "The area of a circle is pi times the radius squared.",
    "The circumference of a circle is 2 pi times the radius.",
    "A hexagon has six sides; an octagon has eight.",
    "Percent means per hundred: 25 percent equals one quarter.",
    "The factorial of 5 is 120.",
    "Two to the tenth power is 1024.",
    "The Fibonacci sequence starts 0, 1, 1, 2, 3, 5, 8, 13.",
    "An even number is divisible by 2 with no remainder.",
    "The sum of the first n integers is n times (n+1) divided by 2.",
    "A dozen is 12; a score is 20.",
    "In Roman numerals, X is 10, L is 50, C is 100, D is 500, and M is 1000.",
]

ASTRONOMY = [
    "The Sun is a G-type main-sequence star at the center of our solar system.",
    "There are eight planets in the solar system.",
    "Mercury is the closest planet to the Sun; Neptune is the farthest.",
    "Venus is the hottest planet due to its dense carbon dioxide atmosphere.",
    "Mars is called the Red Planet because of iron oxide on its surface.",
    "Jupiter is the largest planet in the solar system.",
    "Saturn is famous for its prominent ring system.",
    "Earth is the third planet from the Sun.",
    "The Moon is Earth's only natural satellite.",
    "A solar eclipse occurs when the Moon passes between the Earth and the Sun.",
    "A lunar eclipse occurs when the Earth passes between the Sun and the Moon.",
    "The Milky Way is the galaxy that contains our solar system.",
    "Light from the Sun takes about 8 minutes and 20 seconds to reach Earth.",
    "Pluto was reclassified as a dwarf planet in 2006.",
    "A comet's tail always points away from the Sun.",
    "The International Space Station orbits Earth roughly every 90 minutes.",
    "Neil Armstrong was the first human to walk on the Moon.",
    "Tides are caused mainly by the gravitational pull of the Moon.",
    "Polaris, the North Star, sits nearly above Earth's North Pole.",
    "Galaxies contain billions of stars held together by gravity.",
]

records = []
def add(text, cat):
    records.append({"id": f"core-{len(records)+1:03d}", "text": text,
                    "tags": ["core", cat]})

for country, cap in CAPITALS:
    add(f"The capital of {country} is {cap}.", "capitals")
for name, sym, num in ELEMENTS:
    add(f"The chemical element {name} has symbol {sym} and atomic number {num}.",
        "elements")
for t in CONVERSIONS:
    add(t, "conversions")
for t in DATES:
    add(t, "dates")
for t in SCIENCE:
    add(t, "science")
for t in GEOGRAPHY:
    add(t, "geography")
for t in MATH:
    add(t, "math")
for t in ASTRONOMY:
    add(t, "astronomy")

out = pathlib.Path(__file__).parent / "seed" / "core_facts.jsonl"
if out.exists() and "--force" not in sys.argv:
    raise SystemExit(
        f"REFUSING to overwrite {out} — that file is now canonical and may "
        "contain hand-added facts. Append to it directly, then run "
        "tools/build_seed_pack.py. (--force only to regenerate from scratch.)")
out.parent.mkdir(exist_ok=True)
with open(out, "w") as f:
    for r in records:
        f.write(json.dumps(r, sort_keys=True) + "\n")
print(f"wrote {len(records)} facts to {out}")
