# Fjordvik multistage pumps: service and troubleshooting manual

Document FJV-SM-MS, Edition 3, January 2025. Fjordvik Manufacturing Oy, After-sales Service.

> Synthetic document for a portfolio project. Fjordvik Manufacturing Oy is a fictional company; these instructions describe no real product.

## 1. About this manual

### 1.1 Scope

This manual covers Fjordvik vertical multistage pumps for high pressure at moderate flow. A stack of impeller stages sits on one shaft inside a sleeve. The motor stands on top and carries the axial load; a cartridge mechanical seal sits under the motor stool.

### 1.2 Who may do the work

Only technicians trained by Fjordvik may open the equipment. Work under a service contract must use genuine Fjordvik parts, or the warranty lapses (see the warranty policy, section 3).

## 2. Safety

### 2.1 Isolation

Isolate the supply, lock it off, and prove the equipment dead and depressurised before starting. Tag the isolator with your name and the date.

### 2.2 Hazards of this equipment

Isolate and lock off the motor before any work. Close the valves and release pressure.

## 3. Specification

### 3.1 Models

| Model | Name | Rated power (kW) | Made at |
| --- | --- | --- | --- |
| IPP-MS-011 | Multistage pump 11 kW | 11 | Tampere Plant |
| IPP-MS-022 | Multistage pump 22 kW | 22 | Tampere Plant |
| IPP-MS-045 | Multistage pump 45 kW | 45 | Tampere Plant |

### 3.2 Typical applications

Typical duties: boiler feed, pressure boosting.

## 4. Condition monitoring and alarm limits

### 4.1 What the drive reports

The variable-speed drive reports once a day: running hours, vibration as root mean square (RMS) velocity in millimetres per second, bearing temperature in degrees Celsius, and average power in kilowatts while running. A day with no running shows zero hours and no vibration or temperature reading.

### 4.2 Alarm limits

| Reading | Alert | Alarm |
| --- | --- | --- |
| Vibration (mm/s RMS) | 3.5 | 6.0 |
| Bearing temperature (C) | 75 | 85 |

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

Use SK-MS-01 (Annual service kit, multistage) at every preventive visit.

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

**Parts usually needed.** BR-MS-01 (Bearing set, multistage), CN-GR-01 (Bearing grease cartridge, 400 g).

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

**Parts usually needed.** MS-MS-01 (Mechanical seal, multistage), GK-MS-01 (Gasket and O-ring set, multistage).

### 6.3 Falling flow or head at the same speed (impeller wear)

**Symptoms.** Power falls at the same running hours, the customer reports lower flow or pressure, and vibration rises moderately over weeks.

**Likely causes.**

- Abrasive solids wearing the vanes
- Wear ring clearance grown with age

**Checks.**

- Compare power with the same month last year
- Measure wear ring clearance

**Action.** Replace the impeller and wear rings (section 7.3).

**Parts usually needed.** IM-MS-01 (Impeller stage set, multistage), GK-MS-01 (Gasket and O-ring set, multistage).

### 6.4 Crackling noise and unsteady vibration (cavitation damage)

**Symptoms.** A sound like gravel at the suction side. Vibration rises and becomes uneven from day to day.

**Likely causes.**

- Suction level too low
- Blocked suction strainer
- Inlet valve partly closed
- Running at far higher flow than designed

**Checks.**

- Check suction pressure or level while running
- Check the inlet valve is fully open

**Action.** Correct the suction conditions first, or a new impeller will fail the same way. Then replace the impeller and wear rings (section 7.3).

**Parts usually needed.** IM-MS-01 (Impeller stage set, multistage).

### 6.5 Bearing temperature and power rising together (motor overload)

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

**Parts usually needed.** OK-MS-01 (Overhaul kit, multistage).

### 6.6 Sudden stop with no warning in the readings (electrical trip)

**Symptoms.** The pump stops without any earlier change in vibration, temperature or power. This kind of fault cannot be predicted from the daily readings.

**Likely causes.**

- Supply fault
- Damaged cable or cable entry
- Failed sensor, relay or contactor

**Checks.**

- Read the fault code in the panel or drive
- Test insulation resistance of motor and cable

**Action.** Replace the failed component (section 8) and test before restarting.

**Parts usually needed.** EL-TS-01 (Motor thermal sensor).

## 7. Repair procedures

### 7.1 Bearing replacement

1. Isolate, lock off and depressurise.
2. Lift off the motor; replace the bearing set in the motor stool.

### 7.2 Mechanical seal replacement

1. Remove the motor and coupling.
2. Withdraw the cartridge seal and fit the new one as one unit.

### 7.3 Impeller and wear ring replacement

1. Remove motor and sleeve.
2. Replace the stage set in the order shown on its card.

Tighten every fastener to the torque on the equipment's data plate.

## 8. Parts list

| Part | Name | Family | Lead time (days) |
| --- | --- | --- | --- |
| MS-MS-01 | Mechanical seal, multistage | Mechanical seals | 14 |
| BR-MS-01 | Bearing set, multistage | Bearings | 10 |
| IM-MS-01 | Impeller stage set, multistage | Impellers | 21 |
| GK-MS-01 | Gasket and O-ring set, multistage | Wear rings and gaskets | 7 |
| CN-GR-01 | Bearing grease cartridge, 400 g | Consumables | 5 |
| CN-CI-01 | Coupling insert | Consumables | 7 |
| EL-TS-01 | Motor thermal sensor | Motor and electrical | 10 |
| SK-MS-01 | Annual service kit, multistage | Service kits | 10 |
| OK-MS-01 | Overhaul kit, multistage | Overhaul kits | 21 |

Parts ship from Oulu Warehouse (Nordics) and Tartu Warehouse (Baltics). Lead times apply when a part is not in stock.
