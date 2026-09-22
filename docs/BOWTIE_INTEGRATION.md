# SURM Bowtie Integration

## Purpose

SURM treats the Risk Register as the authoritative source for risk assessment.
The Bowtie layer is a separate, durable diagram artifact keyed by the same risk_id.

## Architecture

Risk Register (SURM methodology)
          |
          v
   bowtie_adapter.py
          |
          v
 bowtie_register[RSK-*]
          |
          +--> Tab 7 interactive SVG editor
          |
          +--> PRA Output read-only renderer
          |
          +--> JSON / SVG export

The Bowtie document follows the structural ideas of gahoward/bowtie-diagram:
https://github.com/gahoward/bowtie-diagram
stable node identities, separate placements, explicit line topology, shared
barriers, JSON persistence, and SVG rendering.

SURM does not import or delegate risk scoring to that project. Likelihood,
impact, risk rating, workflow completion, governance, and study persistence
remain SURM-owned logic.

## Data ownership

| Concern | Owner |
|---|---|
| Risk ID, likelihood, impact, risk rating | SURM Risk Register |
| Uncertainty → risk mapping | SURM master mapping |
| Uncertainty → resolution mapping | SURM Resolution List |
| Cause / barrier / consequence topology | Bowtie document |
| Diagram positions and connections | Bowtie document |
| Study persistence | SURM StudyDocument |
| PRA report | SURM |

## Refresh rule

Existing Bowties are preserved when the Risk Register is repopulated. When
the upstream risk inputs change, the Bowtie receives needs_refresh=True
instead of being silently overwritten. The engineer can explicitly refresh the
diagram from the current Risk Register.

This prevents a later risk-registry rebuild from destroying deliberate manual
Bowtie relationships.

## Current editor scope

- create/delete Cause, Preventive Barrier, Mitigative Barrier and Consequence
- edit node names/descriptions and barrier owner/effectiveness
- drag diagram objects
- auto-arrange
- manage which barriers sit on each Cause/Consequence path
- continuous draft synchronisation to Streamlit session state
- SVG export

The component intentionally does not implement SURM risk scoring. That remains
outside the editor.