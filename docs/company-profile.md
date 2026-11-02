# Fjordvik Manufacturing Oy: company and product profile

The one description of the business that every document in this project uses.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. The emission factors
> are **illustrative**, not cited, and must not be used for real reporting.

## In one line

Fjordvik Manufacturing Oy designs and makes electric pumps and pump systems for water
utilities, industry and buildings, from six sites in Finland, Sweden and Estonia.

## What it makes

| Product family | Typical product groups | Made at | Main customers |
| --- | --- | --- | --- |
| Industrial process pumps | End-suction, split-case and multistage pumps | Tampere Plant, Finland | Pulp and paper, mining, food and chemical plants |
| Water and wastewater pumps | Submersible and dry-installed pumps | Gothenburg Plant, Sweden | Water utilities and municipal wastewater |
| Pump packages and controls | Booster sets, control panels, variable-speed drive packages | Tallinn Plant, Estonia | Buildings, district energy and industry |

Every product is driven by an electric motor, so its energy use over its working life (scope 3
category 11, use of sold products) is by far the largest part of Fjordvik's carbon
footprint: 95% of the 2025 total, worked out from units sold and each model's yearly
electricity use and lifetime. Sales to Rest of world are left out until a grid factor
source for that region is found.

## Sales regions and the product classification

Fjordvik sells in four regions: Nordics, Baltics, Western Europe and Rest of world. Its
global product classification has three levels: 4 families, 10 product groups and 24
product models (the three pump families above, plus spare parts and service kits shipped
from the warehouses). Each business unit in the enterprise resource planning (ERP) system
records sales against its own local item numbers; Gothenburg still uses legacy numbers, so
a mapping table ties every local number to one global product.

## Sites

| Site | Country | Role |
| --- | --- | --- |
| Tampere Plant | Finland | Machines castings and assembles industrial process pumps; rooftop solar panels from July 2024 |
| Helsinki Head Office | Finland | Sales, engineering and group functions; books no revenue of its own |
| Oulu Warehouse | Finland | Spare parts and finished goods for the Nordic market |
| Gothenburg Plant | Sweden | Water and wastewater pumps; buys hydro guarantees of origin for all its electricity |
| Tallinn Plant | Estonia | Pump packages and control panels |
| Tartu Warehouse | Estonia | Spare parts and finished goods for the Baltic market; opened July 2024 |

## Size

EUR 155.0 million revenue and 757 full-time equivalent employees (FTE) in 2025, from the
project's own dataset. That is below the thresholds of the EU's Corporate Sustainability
Reporting Directive (CSRD) after the Omnibus I changes, so Fjordvik reports for its
customers, its lenders and its own targets rather than by law.

## After-sales service

Fjordvik services its pumps in Finland, Sweden, Estonia and Latvia. 150 customers buy its
spare parts and service kits: water utilities, industrial plants, buildings and district
energy companies, and distributors who stock parts for the wider installed base. 600 of
their pumps are connected: each pump's variable-speed drive reports running hours,
vibration, bearing temperature and power once a day. Customers choose no service
contract, Basic (one preventive visit a year) or Premium (two). Twelve technicians work
for the sites in Tampere, Helsinki, Oulu, Gothenburg, Tallinn and Tartu; three of them
start from home towns nearer their customers (Espoo, Borås and Riga). Parts ship from
Oulu Warehouse (Nordics) and Tartu Warehouse (Baltics).

Service today is reactive. A pump fails, the customer calls, parts are ordered after the
failure, and technicians are planned in a spreadsheet. The readings already show most
failures coming weeks ahead, but nobody watches them. The `service-ai` part of this
project is building the forecasting, failure prediction, scheduling, parts suggestions,
service assistant and service desk agent to change that.

## Who owns which figures

| Role | Owns |
| --- | --- |
| Group Sustainability Manager | The emissions figures, emission factors, energy contracts and guarantees of origin |
| Site Energy Coordinator (each site) | The monthly site workbook of energy, fuel, refrigerant, flights and waste |
| Procurement Manager | The purchase ledger in the ERP system |
| Regional controllers | Sales and cost of sales in the ERP, by business unit |
| Portfolio governance | The global product classification and its mapping table |
| Product Managers | Their product groups' quarterly scorecard ratings |
| Logistics Manager | Freight invoices and shipment data from the transport management system |
| Group Financial Controller | Revenue after each monthly close |
| HR Manager | Headcount as FTE |
| Country managers (Finland, Sweden, Estonia) | Their own sites' figures, seen through row-level security |
| Sales region managers (four regions) | Their own region's sales, margin and use-phase emissions |
| Service Manager | The customer and installed pump registers, service contracts, service records and technician planning |
| Technicians | The note and parts on each job they do |
| E-commerce owner | The parts portal and its logs |
| Technical documentation team | The service manuals, service terms and warranty policy |
