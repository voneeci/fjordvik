# Fjordvik submersible pumps: service and troubleshooting manual

Document FJV-SM-SB, Edition 3, January 2025. Fjordvik Manufacturing Oy, After-sales Service.

> Synthetic document for a portfolio project. Fjordvik Manufacturing Oy is a fictional company; these instructions describe no real product.

## 1. About this manual

### 1.1 Scope

This manual covers Fjordvik submersible wastewater pumps with channel impellers, installed in wet wells. Motor and pump form one sealed unit. Two mechanical seals in series, with an oil chamber between them, keep water out of the motor; a moisture sensor in the chamber warns before water reaches the windings. The pump is lifted out on its guide rails.

### 1.2 Who may do the work

Only technicians trained by Fjordvik may open the equipment. Work under a service contract must use genuine Fjordvik parts, or the warranty lapses (see the warranty policy, section 3).

## 2. Safety

### 2.1 Isolation

Isolate the supply, lock it off, and prove the equipment dead and depressurised before starting. Tag the isolator with your name and the date.

### 2.2 Hazards of this equipment

Wet wells can hold toxic or explosive gases. Never enter one without gas testing, ventilation and a standby person; lift the pump out instead.

## 3. Specification

### 3.1 Models

| Model | Name | Rated power (kW) | Made at |
| --- | --- | --- | --- |
| WWP-SB-004 | Submersible pump 4 kW | 4 | Gothenburg Plant |
| WWP-SB-011 | Submersible pump 11 kW | 11 | Gothenburg Plant |
| WWP-SB-022 | Submersible pump 22 kW | 22 | Gothenburg Plant |
| WWP-SB-045 | Submersible pump 45 kW | 45 | Gothenburg Plant |

### 3.2 Typical applications

Typical duties: wastewater lift station, stormwater pumping.

## 4. Condition monitoring and alarm limits

### 4.1 What the drive reports

The variable-speed drive reports once a day: running hours, vibration as root mean square (RMS) velocity in millimetres per second, bearing temperature in degrees Celsius, and average power in kilowatts while running. A day with no running shows zero hours and no vibration or temperature reading.

### 4.2 Alarm limits

| Reading | Alert | Alarm |
| --- | --- | --- |
| Vibration (mm/s RMS) | 5.0 | 8.0 |
| Bearing temperature (C) | 70 | 80 |

At **alert**, plan a visit within two weeks. At **alarm**, stop the pump if the customer can manage without it, and repair before restarting. These are Fjordvik's own limits for this product group.

### 4.3 Reading the trends

Judge the trend, not one reading. A single high vibration reading after a start is a transient and needs no action. A steady rise over two to six weeks is the usual warning of bearing wear, cavitation or impeller wear. Some faults, such as seal leaks and electrical trips, often give no warning at all.

## 5. Preventive maintenance

### 5.1 Intervals

| Service contract | Preventive visits a year |
| --- | --- |
| None | 0 |
| Basic | 1 |
| Premium | 2 |

Without a contract, Fjordvik recommends one visit a year; the customer books it.

### 5.2 Service kit

Use SK-SB-01 (Annual service kit, submersible) at every preventive visit.

### 5.3 Checklist

1. Read the last three months of readings before the visit.
2. Inspect for leaks, corrosion and loose fixings.
3. Fit the service kit and regrease where fitted with grease nipples.
4. Record vibration and bearing temperature after 30 minutes of running.
5. Write what you saw in the work order note, including anything to watch.

## 6. Troubleshooting

### 6.1 Rising vibration with bearing noise (bearing wear)

**Symptoms.** Vibration climbs steadily over two to six weeks. Bearing temperature often follows in the last days. Noise or roughness can be heard at the bearing housing.

**Likely causes.**

- Lubricant old, contaminated or missing
- Misalignment between pump and motor
- Running far from the duty point
- Age and long running hours

**Checks.**

- Compare vibration with the last three months, not with a single reading
- Check alignment with the coupling disconnected
- Listen at both bearing housings

**Action.** Plan a bearing replacement (section 7.1) before vibration reaches the alarm limit. A planned stop costs far less than a seized bearing.

**Parts usually needed.** BR-SB-01 (Bearing set, submersible motor).

### 6.2 Leak at the shaft seal (mechanical seal leak)

**Symptoms.** Liquid at the seal, under the pump or in the seal chamber. Vibration and temperature usually show nothing beforehand, so the monitoring rarely gives warning.

**Likely causes.**

- Dry running, even briefly
- Abrasive solids in the pumped liquid
- Worn or cracked seal faces
- Wrong or blocked seal flushing

**Checks.**

- Find where the liquid comes from before opening the pump
- Check that the pump cannot run dry (level or pressure switch)

**Action.** Replace the mechanical seal and its O-rings (section 7.2). Never reuse seal faces.

**Parts usually needed.** MS-SB-01 (Double seal cartridge, submersible), GK-SB-01 (O-ring set, submersible).

### 6.3 Falling flow or head at the same speed (impeller wear)

**Symptoms.** Power falls at the same running hours, the customer reports lower flow or pressure, and vibration rises moderately over weeks.

**Likely causes.**

- Abrasive solids wearing the vanes
- Wear ring clearance grown with age

**Checks.**

- Compare power with the same month last year
- Measure wear ring clearance

**Action.** Replace the impeller and wear rings (section 7.3).

**Parts usually needed.** IM-SB-S1 (Channel impeller, submersible up to 11 kW), IM-SB-L1 (Channel impeller, submersible 22 to 45 kW), WR-SB-01 (Wear plate, submersible), GK-SB-01 (O-ring set, submersible).

### 6.4 Bearing temperature and power rising together (motor overload)

**Symptoms.** Bearing temperature and power climb together over days or weeks until the motor protection trips.

**Likely causes.**

- Duty point moved (system changes)
- Thicker liquid than designed
- Blocked motor cooling
- Failing bearings adding friction

**Checks.**

- Measure motor current against the nameplate
- Check cooling air or jacket flow

**Action.** Find and remove the cause, then overhaul the pump with the overhaul kit (section 8).

**Parts usually needed.** OK-SB-01 (Overhaul kit, submersible).

### 6.5 Sudden stop with no warning in the readings (electrical trip)

**Symptoms.** The pump stops without any earlier change in vibration, temperature or power. This kind of fault cannot be predicted from the daily readings.

**Likely causes.**

- Supply fault
- Damaged cable or cable entry
- Failed sensor, relay or contactor

**Checks.**

- Read the fault code in the panel or drive
- Test insulation resistance of motor and cable

**Action.** Replace the failed component (section 8) and test before restarting.

**Parts usually needed.** EL-MS-01 (Moisture sensor, seal chamber), EL-TS-01 (Motor thermal sensor), EL-CE-01 (Cable entry kit), EL-LC-01 (Level controller).

### 6.6 Power rising and the pump cycling (impeller clogging)

**Symptoms.** Power rises, flow falls and the pump starts and stops more often. Rags and wet wipes are the usual cause.

**Likely causes.**

- Rags, wipes and fibres in the wastewater
- Non-return valve stuck

**Checks.**

- Check the pump's start count against the last month
- Check the non-return valve

**Action.** Lift or open the pump and clear the impeller channel. Renew the gaskets disturbed. Advise the customer on screening or an information campaign about wipes.

**Parts usually needed.** GK-SB-01 (O-ring set, submersible).

## 7. Repair procedures

### 7.1 Bearing replacement

1. Isolate and lock off at the panel; lift the pump on its chain. Never enter the wet well without gas testing and a standby person.
2. Drain the oil chamber and open the motor end.
3. Replace both motor bearings; refill the oil chamber with new oil.

### 7.2 Mechanical seal replacement

1. Lift the pump and drain the oil chamber.
2. Replace both seals as the cartridge set; renew the O-rings.
3. Test the moisture sensor before lowering the pump.

### 7.3 Impeller and wear ring replacement

1. Lift the pump; remove the volute.
2. Replace the channel impeller and wear plate; set the gap with the adjusting screws.

Tighten every fastener to the torque on the equipment's data plate.

## 8. Parts list

| Part | Name | Family | Lead time (days) |
| --- | --- | --- | --- |
| MS-SB-01 | Double seal cartridge, submersible | Mechanical seals | 21 |
| BR-SB-01 | Bearing set, submersible motor | Bearings | 14 |
| IM-SB-S1 | Channel impeller, submersible up to 11 kW | Impellers | 21 |
| IM-SB-L1 | Channel impeller, submersible 22 to 45 kW | Impellers | 28 |
| WR-SB-01 | Wear plate, submersible | Wear rings and gaskets | 14 |
| GK-SB-01 | O-ring set, submersible | Wear rings and gaskets | 7 |
| CN-OL-01 | Seal chamber oil, 1 litre | Consumables | 5 |
| EL-MS-01 | Moisture sensor, seal chamber | Motor and electrical | 14 |
| EL-TS-01 | Motor thermal sensor | Motor and electrical | 10 |
| EL-CE-01 | Cable entry kit | Motor and electrical | 14 |
| EL-LC-01 | Level controller | Motor and electrical | 14 |
| SK-SB-01 | Annual service kit, submersible | Service kits | 10 |
| OK-SB-01 | Overhaul kit, submersible | Overhaul kits | 28 |

Parts ship from Oulu Warehouse (Nordics) and Tartu Warehouse (Baltics). Lead times apply when a part is not in stock.
