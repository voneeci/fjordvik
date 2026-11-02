"""Fjordvik's service manuals, service terms and warranty policy, as Markdown.

The documents are written from templates and the settings in config.py, so the
models, alarm limits, service intervals and part numbers they quote always match
the data. One manual per product group with equipment, numbered sections
throughout ("## 4." and "### 4.2") so an assistant can cite them. All synthetic:
Fjordvik Manufacturing Oy is fictional, and so are its terms.
"""

import hashlib
import json
from pathlib import Path

from fjordvik_data import config as c

EDITION = "Edition 3, January 2025"
NOTICE = ("> Synthetic document for a portfolio project. Fjordvik Manufacturing Oy is a "
          "fictional company; these instructions describe no real product.")

GROUPS = {   # group: (document code, file name, what it is, how it is built)
    "End-suction pumps": (
        "SM-ES", "manual-end-suction-pumps.md",
        "single-stage end-suction centrifugal pumps on a baseplate, driven by a standard "
        "motor through a flexible coupling",
        "The rotating unit pulls out from the back of the casing, so the casing and pipework "
        "stay in place during repairs. Two grease-lubricated rolling bearings carry the shaft, "
        "and a single mechanical seal closes the shaft passage."),
    "Split-case pumps": (
        "SM-SC", "manual-split-case-pumps.md",
        "axially split double-suction pumps for large flows",
        "The casing splits along the shaft, so the upper half lifts off and the rotor comes out "
        "without disturbing the pipework or the motor. A bearing at each end carries the "
        "shaft, with a mechanical seal on each side of the impeller."),
    "Multistage pumps": (
        "SM-MS", "manual-multistage-pumps.md",
        "vertical multistage pumps for high pressure at moderate flow",
        "A stack of impeller stages sits on one shaft inside a sleeve. The motor stands on top "
        "and carries the axial load; a cartridge mechanical seal sits under the motor stool."),
    "Submersible pumps": (
        "SM-SB", "manual-submersible-pumps.md",
        "submersible wastewater pumps with channel impellers, installed in wet wells",
        "Motor and pump form one sealed unit. Two mechanical seals in series, with an oil "
        "chamber between them, keep water out of the motor; a moisture sensor in the chamber "
        "warns before water reaches the windings. The pump is lifted out on its guide rails."),
    "Dry-installed pumps": (
        "SM-DI", "manual-dry-installed-pumps.md",
        "dry-installed wastewater and sludge pumps in pump rooms",
        "The pump stands beside the wet well, connected by pipework. The back pull-out design "
        "lets the motor, bearing bracket and impeller come out as one unit."),
    "Booster sets": (
        "SM-BS", "manual-booster-sets.md",
        "packaged booster sets of two or three multistage pumps on a common frame, with a "
        "control panel and a variable-speed drive",
        "Each pump in the set is a Fjordvik multistage pump (see the multistage manual for its "
        "own repairs). The set adds manifolds, non-return valves, a pressure sensor and the "
        "panel that shares the duty between the pumps."),
    "Control panels": (
        "SM-CP", "manual-control-panels.md",
        "pump control panels for single pumps and duty and standby pairs",
        "The panel holds the main switch, contactors, motor protection relays and a level or "
        "pressure controller. It records fault codes and alternates duty between pumps."),
    "Drive packages": (
        "SM-VD", "manual-drive-packages.md",
        "variable-speed drive packages that power a pump and report its condition",
        "The drive adjusts motor speed to the demand and reports the pump's running hours, "
        "vibration, bearing temperature and power once a day to Fjordvik's monitoring service."),
}

TROUBLE = {  # mode: (symptom heading, symptoms, causes, checks, action)
    "Bearing wear": (
        "Rising vibration with bearing noise",
        "Vibration climbs steadily over two to six weeks. Bearing temperature often follows in "
        "the last days. Noise or roughness can be heard at the bearing housing.",
        ["Lubricant old, contaminated or missing", "Misalignment between pump and motor",
         "Running far from the duty point", "Age and long running hours"],
        ["Compare vibration with the last three months, not with a single reading",
         "Check alignment with the coupling disconnected", "Listen at both bearing housings"],
        "Plan a bearing replacement (section 7.1) before vibration reaches the alarm limit. A "
        "planned stop costs far less than a seized bearing."),
    "Mechanical seal leak": (
        "Leak at the shaft seal",
        "Liquid at the seal, under the pump or in the seal chamber. Vibration and temperature "
        "usually show nothing beforehand, so the monitoring rarely gives warning.",
        ["Dry running, even briefly", "Abrasive solids in the pumped liquid",
         "Worn or cracked seal faces", "Wrong or blocked seal flushing"],
        ["Find where the liquid comes from before opening the pump",
         "Check that the pump cannot run dry (level or pressure switch)"],
        "Replace the mechanical seal and its O-rings (section 7.2). Never reuse seal faces."),
    "Impeller wear": (
        "Falling flow or head at the same speed",
        "Power falls at the same running hours, the customer reports lower flow or pressure, "
        "and vibration rises moderately over weeks.",
        ["Abrasive solids wearing the vanes", "Wear ring clearance grown with age"],
        ["Compare power with the same month last year", "Measure wear ring clearance"],
        "Replace the impeller and wear rings (section 7.3)."),
    "Cavitation damage": (
        "Crackling noise and unsteady vibration",
        "A sound like gravel at the suction side. Vibration rises and becomes uneven from day to "
        "day.",
        ["Suction level too low", "Blocked suction strainer", "Inlet valve partly closed",
         "Running at far higher flow than designed"],
        ["Check suction pressure or level while running", "Check the inlet valve is fully open"],
        "Correct the suction conditions first, or a new impeller will fail the same way. Then "
        "replace the impeller and wear rings (section 7.3)."),
    "Motor overload": (
        "Bearing temperature and power rising together",
        "Bearing temperature and power climb together over days or weeks until the motor "
        "protection trips.",
        ["Duty point moved (system changes)", "Thicker liquid than designed",
         "Blocked motor cooling", "Failing bearings adding friction"],
        ["Measure motor current against the nameplate", "Check cooling air or jacket flow"],
        "Find and remove the cause, then overhaul the pump with the overhaul kit (section 8)."),
    "Electrical trip": (
        "Sudden stop with no warning in the readings",
        "The pump stops without any earlier change in vibration, temperature or power. This "
        "kind of fault cannot be predicted from the daily readings.",
        ["Supply fault", "Damaged cable or cable entry", "Failed sensor, relay or contactor"],
        ["Read the fault code in the panel or drive", "Test insulation resistance of motor and cable"],
        "Replace the failed component (section 8) and test before restarting."),
    "Impeller clogging": (
        "Power rising and the pump cycling",
        "Power rises, flow falls and the pump starts and stops more often. Rags and wet wipes "
        "are the usual cause.",
        ["Rags, wipes and fibres in the wastewater", "Non-return valve stuck"],
        ["Check the pump's start count against the last month", "Check the non-return valve"],
        "Lift or open the pump and clear the impeller channel. Renew the gaskets disturbed. "
        "Advise the customer on screening or an information campaign about wipes."),
}

PROCEDURES = {
    "End-suction pumps": [
        ("Bearing replacement", ["Isolate and lock off the motor; close the inlet and outlet valves.",
                                 "Remove the coupling guard and the coupling spacer.",
                                 "Unbolt the bearing bracket and pull the rotating unit out from the back.",
                                 "Press off both bearings and fit the new set; grease as section 5.",
                                 "Refit, align the coupling and run for 30 minutes, checking vibration."]),
        ("Mechanical seal replacement", ["Pull out the rotating unit as for bearings.",
                                         "Remove the impeller nut and impeller; slide off the seal.",
                                         "Clean the shaft, fit the new seal with new O-rings, refit the impeller."]),
        ("Impeller and wear ring replacement", ["Pull out the rotating unit.",
                                                "Replace the impeller and both wear rings; check clearance on the data plate."]),
    ],
    "Split-case pumps": [
        ("Bearing replacement", ["Isolate and lock off; drain the casing.",
                                 "Remove the bearing covers at both ends.",
                                 "Lift the upper casing half with the lifting lugs only.",
                                 "Lift the rotor out, replace both bearings, refit with new casing gasket."]),
        ("Mechanical seal replacement", ["Lift out the rotor as for bearings.",
                                         "Replace both seals; the two sides are identical but mirrored."]),
        ("Impeller and wear ring replacement", ["Lift out the rotor; press off the impeller.",
                                                "Fit the new impeller and wear rings; rebalance if the "
                                                "workshop has the equipment."]),
    ],
    "Multistage pumps": [
        ("Bearing replacement", ["Isolate, lock off and depressurise.",
                                 "Lift off the motor; replace the bearing set in the motor stool."]),
        ("Mechanical seal replacement", ["Remove the motor and coupling.",
                                         "Withdraw the cartridge seal and fit the new one as one unit."]),
        ("Impeller and wear ring replacement", ["Remove motor and sleeve.",
                                                "Replace the stage set in the order shown on its card."]),
    ],
    "Submersible pumps": [
        ("Bearing replacement", ["Isolate and lock off at the panel; lift the pump on its chain. "
                                 "Never enter the wet well without gas testing and a standby person.",
                                 "Drain the oil chamber and open the motor end.",
                                 "Replace both motor bearings; refill the oil chamber with new oil."]),
        ("Mechanical seal replacement", ["Lift the pump and drain the oil chamber.",
                                         "Replace both seals as the cartridge set; renew the O-rings.",
                                         "Test the moisture sensor before lowering the pump."]),
        ("Impeller and wear ring replacement", ["Lift the pump; remove the volute.",
                                                "Replace the channel impeller and wear plate; set the gap "
                                                "with the adjusting screws."]),
    ],
    "Dry-installed pumps": [
        ("Bearing replacement", ["Isolate and lock off; close the valves and drain the casing.",
                                 "Pull out the motor, bearing bracket and impeller as one unit.",
                                 "Replace the bearings in the bracket; regrease."]),
        ("Mechanical seal replacement", ["Pull out the rotating unit.",
                                         "Replace the seal and O-rings."]),
        ("Impeller and wear ring replacement", ["Pull out the rotating unit.",
                                                "Replace the impeller and wear rings; check the gap."]),
    ],
    "Booster sets": [
        ("Pump replacement in the set", ["Switch the set to manual and isolate the one pump; the "
                                         "others keep pressure.",
                                         "Close its valves, unbolt it from the manifolds and lift it out.",
                                         "Repair it as the multistage manual says, or fit an exchange pump."]),
        ("Pressure sensor and drive check", ["Compare the sensor reading with a test gauge.",
                                             "Clean or replace the drive filter mats."]),
    ],
    "Control panels": [
        ("Contactor or relay replacement", ["Switch off the main switch and lock it.",
                                            "Prove the panel dead before touching anything.",
                                            "Replace the part; set the relay to the motor nameplate current."]),
        ("Level controller replacement", ["Note the start and stop levels.",
                                          "Fit the new controller and enter the same levels."]),
    ],
    "Drive packages": [
        ("Cooling fan replacement", ["Isolate and wait for the capacitors to discharge (the drive "
                                     "display shows when it is safe).",
                                     "Replace the fan; check it runs in the right direction."]),
        ("Filter mat replacement", ["Open the door filter housing and replace the mats."]),
    ],
}

HAZARDS = {
    "Submersible pumps": "Wet wells can hold toxic or explosive gases. Never enter one without gas "
                         "testing, ventilation and a standby person; lift the pump out instead.",
    "Dry-installed pumps": "Wastewater can carry infection: wear gloves and eye protection, and "
                           "wash before eating.",
    "Control panels": "Panels hold live parts. Only qualified electricians open them, after "
                      "proving them dead.",
    "Drive packages": "Drives store charge after switch-off. Wait until the display shows it "
                      "is safe before opening the cover.",
}
HOT_WATER = "Heating circulation pumps carry hot water under pressure: let them cool and depressurise first."


def models(group: str) -> list[tuple]:
    return [p for p in c.PRODUCTS if p[2] == group]


def parts_for(group: str) -> list[tuple]:
    return [p for p in c.PARTS if group in p[6]]


def table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


def repair_parts(mode: str, group: str) -> str:
    names = []
    for selector, _q in c.REPAIR_PARTS[mode]:
        for p in parts_for(group):
            if p[2] == selector or p[0].startswith(selector + "-"):
                names.append(f"{p[0]} ({p[1]})")
    return ", ".join(dict.fromkeys(names)) or "see section 8"


def manual(group: str) -> str:
    code, _file, what, build = GROUPS[group]
    is_pump = group in c.PUMP_GROUPS
    s = [f"# Fjordvik {group.lower()}: service and troubleshooting manual", "",
         f"Document FJV-{code}, {EDITION}. Fjordvik Manufacturing Oy, After-sales Service.", "",
         NOTICE, "",
         "## 1. About this manual", "",
         "### 1.1 Scope", "",
         f"This manual covers Fjordvik {what}. {build}", "",
         "### 1.2 Who may do the work", "",
         "Only technicians trained by Fjordvik may open the equipment. Work under a service "
         "contract must use genuine Fjordvik parts, or the warranty lapses (see the warranty "
         "policy, section 3).", ""]
    hazards = HAZARDS.get(group, "Isolate and lock off the motor before any work. Close the "
                                 "valves and release pressure.")
    s += ["## 2. Safety", "", "### 2.1 Isolation", "",
          "Isolate the supply, lock it off, and prove the equipment dead and depressurised before "
          "starting. Tag the isolator with your name and the date.", "",
          "### 2.2 Hazards of this equipment", "", hazards, ""]
    if any(a[3] == "heating" for a in c.APPLICATIONS.get(group, [])):
        s += [HOT_WATER, ""]
    s += ["## 3. Specification", "", "### 3.1 Models", "",
          table(["Model", "Name", "Rated power (kW)", "Made at"],
                [[p[0], p[1], p[4] or "not applicable",
                  next(n for sid, n, *_ in c.SITES if sid == p[3])] for p in models(group)]), ""]
    if is_pump:
        apps = ", ".join(a[0].lower() for a in c.APPLICATIONS[group])
        s += ["### 3.2 Typical applications", "", f"Typical duties: {apps}.", ""]
        vib_alert, vib_alarm, t_alert, t_alarm = c.ALARM_LIMITS[group]
        s += ["## 4. Condition monitoring and alarm limits", "",
              "### 4.1 What the drive reports", "",
              "The variable-speed drive reports once a day: running hours, vibration as root "
              "mean square (RMS) velocity in millimetres per second, bearing temperature in "
              "degrees Celsius, and average power in kilowatts while running. A day with no "
              "running shows zero hours and no vibration or temperature reading.", "",
              "### 4.2 Alarm limits", "",
              table(["Reading", "Alert", "Alarm"],
                    [["Vibration (mm/s RMS)", vib_alert, vib_alarm],
                     ["Bearing temperature (C)", t_alert, t_alarm]]), "",
              "At **alert**, plan a visit within two weeks. At **alarm**, stop the pump if the "
              "customer can manage without it, and repair before restarting. These are "
              "Fjordvik's own limits for this product group.", "",
              "### 4.3 Reading the trends", "",
              "Judge the trend, not one reading. A single high vibration reading after a start "
              "is a transient and needs no action. A steady rise over two to six weeks is the "
              "usual warning of bearing wear, cavitation or impeller wear. Some faults, such as "
              "seal leaks and electrical trips, often give no warning at all.", ""]
    else:
        s += ["## 4. Fault indications", "", "### 4.1 Fault codes", "",
              "The equipment records each fault with a code and time. Read the log before "
              "resetting anything, and note the codes on the work order.", ""]
    kit = next((p for p in parts_for(group) if p[2] == "Service kits"), None)
    s += ["## 5. Preventive maintenance", "", "### 5.1 Intervals", "",
          table(["Service contract", "Preventive visits a year"],
                [[k, v] for k, v in c.PREVENTIVE_VISITS_PER_YEAR.items()]), "",
          "Without a contract, Fjordvik recommends one visit a year; the customer books it.", "",
          "### 5.2 Service kit", "",
          (f"Use {kit[0]} ({kit[1]}) at every preventive visit." if kit else
           "This equipment has no service kit; use the parts in section 8 as needed."), "",
          "### 5.3 Checklist", "",
          "1. Read the last three months of readings before the visit.",
          "2. Inspect for leaks, corrosion and loose fixings.",
          "3. Fit the service kit and regrease where fitted with grease nipples.",
          "4. Record vibration and bearing temperature after 30 minutes of running.",
          "5. Write what you saw in the work order note, including anything to watch.", ""]
    modes = [m for m in c.FAILURE_MODES if group in c.MODE_GROUPS.get(m, {group})] if is_pump \
        else ["Electrical trip"]
    s += ["## 6. Troubleshooting", ""]
    for n, mode in enumerate(modes, 1):
        heading, symptoms, causes, checks, action = TROUBLE[mode]
        s += [f"### 6.{n} {heading} ({mode.lower()})", "", f"**Symptoms.** {symptoms}", "",
              "**Likely causes.**", ""] + [f"- {x}" for x in causes] + [
              "", "**Checks.**", ""] + [f"- {x}" for x in checks] + [
              "", f"**Action.** {action}", "",
              f"**Parts usually needed.** {repair_parts(mode, group) if is_pump else 'see section 8'}.", ""]
    s += ["## 7. Repair procedures", ""]
    for n, (title, steps) in enumerate(PROCEDURES[group], 1):
        s += [f"### 7.{n} {title}", ""] + [f"{i}. {x}" for i, x in enumerate(steps, 1)] + [""]
    s += ["Tighten every fastener to the torque on the equipment's data plate.", "",
          "## 8. Parts list", "",
          table(["Part", "Name", "Family", "Lead time (days)"],
                [[p[0], p[1], p[2], p[5]] for p in parts_for(group)]), "",
          "Parts ship from Oulu Warehouse (Nordics) and Tartu Warehouse (Baltics). Lead times "
          "apply when a part is not in stock.", ""]
    return "\n".join(s)


def service_terms() -> str:
    visits = c.PREVENTIVE_VISITS_PER_YEAR
    return "\n".join([
        "# Fjordvik service terms", "", f"Document FJV-ST, {EDITION}.", "", NOTICE, "",
        "## 1. Scope", "",
        "These terms apply to service work on Fjordvik pumps, panels and drives in Finland, "
        "Sweden, Estonia and Latvia. Elsewhere, Fjordvik's distributors serve customers on "
        "their own terms.", "",
        "## 2. Service contracts", "",
        table(["Contract", "Preventive visits a year", "Remote monitoring", "Response to a breakdown"],
              [["None", visits["None"], "No", "Best effort, quoted per job"],
               ["Basic", visits["Basic"], "Readings stored, reviewed at visits", "Within 3 business days"],
               ["Premium", visits["Premium"], "Readings stored, reviewed at visits",
                "Technician on site within 24 hours on business days"]]), "",
        "### 2.1 What a preventive visit includes", "",
        "Labour, travel and the service kit for each covered unit. Repairs found during the "
        "visit are quoted separately.", "",
        "### 2.2 Changing contract", "",
        "A customer can move up a level at any time and down a level at the yearly renewal.", "",
        "## 3. Parts", "",
        "### 3.1 Genuine parts", "",
        "Fjordvik fits genuine parts only. Prices follow the customer's parts price list.", "",
        "### 3.2 Delivery", "",
        "Parts in stock ship the same business day from Oulu Warehouse or Tartu Warehouse. "
        "Parts not in stock take the lead time in the manual's parts list.", "",
        "### 3.3 Returns", "",
        "Unused parts in their original packaging can be returned within 30 days of delivery.", "",
        "## 4. Readings from connected pumps", "",
        "Pumps with a Fjordvik drive send daily readings to Fjordvik. The customer owns the "
        "readings; Fjordvik uses them to plan service and improve its products, and shares "
        "them with no one else without the customer's consent.", "",
        "## 5. Work orders and approval", "",
        "Every job has a work order with a unique number. Work beyond the agreed scope needs "
        "the customer's approval first, except to make the site safe.", ""])


def warranty_policy() -> str:
    return "\n".join([
        "# Fjordvik warranty policy", "", f"Document FJV-WP, {EDITION}.", "", NOTICE, "",
        "## 1. Warranty period", "",
        "Fjordvik equipment is under warranty for 24 months from installation, and at most 30 "
        "months from delivery, whichever ends first.", "",
        "## 2. What is covered", "",
        "Defects in materials or manufacture that appear in normal use within the period. "
        "Fjordvik repairs or replaces the faulty part, and pays the labour and travel for "
        "the repair.", "",
        "## 3. What is not covered", "",
        "- Wear parts (mechanical seals, bearings, impellers, wear rings, gaskets, filter mats), "
        "unless they fail within 6 months of installation",
        "- Damage from dry running, cavitation caused by poor suction conditions, or clogging "
        "by foreign objects",
        "- Damage from parts that are not genuine Fjordvik parts",
        "- Equipment under a service contract whose preventive visits were refused", "",
        "## 4. Making a claim", "",
        "Claim within 30 days of finding the fault, with the serial number, a description and "
        "photographs. Keep the faulty part until Fjordvik decides the claim.", "",
        "## 5. Parts replaced under warranty", "",
        "A part replaced under warranty is covered for 12 months, or for the rest of the "
        "original period if that is longer.", "",
        "## 6. Decisions", "",
        "Fjordvik's After-sales Service decides claims within 10 business days of receiving "
        "everything listed in section 4.", ""])


def documents() -> dict[str, str]:
    docs = {GROUPS[g][1]: manual(g) for g in GROUPS}
    docs["service-terms.md"] = service_terms()
    docs["warranty-policy.md"] = warranty_policy()
    return docs


def write_corpus(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"corpus": "Fjordvik service documents (synthetic)", "documents": {}}
    for name, text in documents().items():
        path = out_dir / name
        path.write_text(text, encoding="utf-8", newline="\n")
        manifest["documents"][name] = {
            "title": text.splitlines()[0].lstrip("# "),
            "sections": sum(1 for line in text.splitlines() if line.startswith("## ")),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8", newline="\n")
    return manifest
