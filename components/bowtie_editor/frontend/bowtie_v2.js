/* global window, document, XMLSerializer, Blob, URL, Image */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const GRID = 20;
  const VIEW_W = 1600;
  const VIEW_H = 900;
  const MIN_Y = 130;
  const MAX_Y = 770;
  const LANE_X = {
    cause: 170,
    preventativeBarrier: 500,
    topLevelEvent: 800,
    mitigativeBarrier: 1100,
    outcome: 1430,
  };
  const COLORS = {
    cause: { fill: "#f7e8c5", stroke: "#b57a17" },
    preventativeBarrier: { fill: "#e5f4ec", stroke: "#168a62" },
    mitigativeBarrier: { fill: "#ece9fb", stroke: "#564ab5" },
    outcome: { fill: "#f8e4dc", stroke: "#a84c2f" },
  };

  let args = null;
  let editable = true;
  let doc = null;
  let selected = null;
  let dirtyTimer = null;
  let undoStack = [];
  let redoStack = [];
  let historySuspended = false;
  let dragState = null;
  let panState = null;
  let camera = { x: 0, y: 0, w: VIEW_W, h: VIEW_H };

  const svg = document.getElementById("svg");
  const objectsEl = document.getElementById("objects");
  const editorEl = document.getElementById("editor");
  const relationshipsEl = document.getElementById("relationships");
  const statusEl = document.getElementById("status");
  const healthEl = document.getElementById("health");
  const zoomResetEl = document.getElementById("zoomReset");

  function post(type, data) {
    const message = Object.assign(
      {isStreamlitMessage:true, type:type},
      data || {}
    );
    window.parent.postMessage(message, "*");
  }

  function ready(height) {
    post("streamlit:componentReady", {apiVersion:1});
    post("streamlit:setFrameHeight", {height:Number(height) || 820});
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function esc(value) {
    return String(value == null ? "" : value).replace(
      /[&<>"']/g,
      function (m) {
        return {
          "&":"&amp;",
          "<":"&lt;",
          ">":"&gt;",
          '"':"&quot;",
          "'":"&#39;",
        }[m];
      }
    );
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function snap(value) {
    return Math.round(value / GRID) * GRID;
  }

  function finite(value, fallback) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function itemsFor(type) {
    if (!doc) return [];
    if (type === "cause") return doc.causes;
    if (type === "outcome") return doc.outcomes;
    if (type === "preventativeBarrier") return doc.preventativeBarriers;
    return doc.mitigativeBarriers;
  }

  function allPlacements() {
    return [
      ...(doc ? doc.causes : []),
      ...(doc ? doc.preventativeBarriers : []),
      ...(doc ? doc.mitigativeBarriers : []),
      ...(doc ? doc.outcomes : []),
    ];
  }

  function nodeFor(placement) {
    if (!placement || !doc) return null;
    const bucket = doc.library[placement.type] || [];
    return bucket.find(function (node) {
      return node.id === placement.nodeId;
    }) || null;
  }

  function placementForId(id) {
    return allPlacements().find(function (p) { return p.id === id; }) || null;
  }

  function lineForOrigin(id) {
    return (doc.lines || []).find(function (line) {
      return line.originId === id;
    }) || null;
  }

  function normalizeDocument(raw) {
    const value = clone(raw || {});
    value.name = String(value.name || "SURM Bowtie");
    value.risk_id = String(value.risk_id || "");
    value.editor_revision = finite(value.editor_revision, 0);
    value.layout_version = 2;
    value.pages = Array.isArray(value.pages) ? value.pages : [];
    value.lines = Array.isArray(value.lines) ? value.lines : [];
    value.causes = Array.isArray(value.causes) ? value.causes : [];
    value.preventativeBarriers = Array.isArray(value.preventativeBarriers) ? value.preventativeBarriers : [];
    value.mitigativeBarriers = Array.isArray(value.mitigativeBarriers) ? value.mitigativeBarriers : [];
    value.outcomes = Array.isArray(value.outcomes) ? value.outcomes : [];
    value.library = value.library || {};
    value.library.cause = Array.isArray(value.library.cause) ? value.library.cause : [];
    value.library.preventativeBarrier = Array.isArray(value.library.preventativeBarrier) ? value.library.preventativeBarrier : [];
    value.library.mitigativeBarrier = Array.isArray(value.library.mitigativeBarrier) ? value.library.mitigativeBarrier : [];
    value.library.outcome = Array.isArray(value.library.outcome) ? value.library.outcome : [];
    value.layout = value.layout || {};

    value.causes.forEach(function (p, i) {
      p.type = "cause";
      p.w = Math.max(finite(p.w, 240), 220);
      p.h = Math.max(finite(p.h, 86), 76);
      p.x = LANE_X.cause;
      p.y = clamp(finite(p.y, 180 + i * 110), MIN_Y, MAX_Y);
      p.pageId = p.pageId || "PAGE_1";
    });

    value.preventativeBarriers.forEach(function (p, i) {
      p.type = "preventativeBarrier";
      p.w = Math.max(finite(p.w, 150), 140);
      p.h = Math.max(finite(p.h, 110), 100);
      if (!Number.isFinite(Number(p.y))) {
        p.y = 180 + i * 110;
      }
      p.x = LANE_X.preventativeBarrier;
      p.y = clamp(Number(p.y), MIN_Y, MAX_Y);
      p.pageId = p.pageId || "PAGE_1";
    });

    value.mitigativeBarriers.forEach(function (p, i) {
      p.type = "mitigativeBarrier";
      p.w = Math.max(finite(p.w, 150), 140);
      p.h = Math.max(finite(p.h, 110), 100);
      if (!Number.isFinite(Number(p.y))) {
        p.y = 180 + i * 110;
      }
      p.x = LANE_X.mitigativeBarrier;
      p.y = clamp(Number(p.y), MIN_Y, MAX_Y);
      p.pageId = p.pageId || "PAGE_1";
    });

    value.outcomes.forEach(function (p, i) {
      p.type = "outcome";
      p.w = Math.max(finite(p.w, 240), 220);
      p.h = Math.max(finite(p.h, 86), 76);
      p.x = LANE_X.outcome;
      p.y = clamp(finite(p.y, 180 + i * 110), MIN_Y, MAX_Y);
      p.pageId = p.pageId || "PAGE_1";
    });

    value.library.preventativeBarrier.concat(value.library.mitigativeBarrier).forEach(function (n) {
      n.degradation_factors = Array.isArray(n.degradation_factors) ? n.degradation_factors : [];
      n.controls = Array.isArray(n.controls) ? n.controls : [];
    });

    if (!value.pages.length) {
      value.pages.push({
        id: "PAGE_1",
        name: value.name || "Risk Bowtie",
        description: "SURM Risk Bowtie",
        topLevelEvent: { id: "TLE_1", name: value.name || "Top Event" },
        hazard: { id: "HAZARD_1", name: "Subsurface Risk" },
      });
    }

    syncLayoutMetadata(value);
    return value;
  }

  function syncLayoutMetadata(target) {
    const targetDoc = target || doc;
    if (!targetDoc) return;
    targetDoc.layout_version = 2;
    targetDoc.layout = targetDoc.layout || {};
    allPlacementsFor(targetDoc).forEach(function (p) {
      targetDoc.layout[p.id] = {
        x: finite(p.x, 0),
        y: finite(p.y, 0),
        w: finite(p.w, 0),
        h: finite(p.h, 0),
      };
    });
  }

  function allPlacementsFor(targetDoc) {
    return [
      ...(targetDoc.causes || []),
      ...(targetDoc.preventativeBarriers || []),
      ...(targetDoc.mitigativeBarriers || []),
      ...(targetDoc.outcomes || []),
    ];
  }

  function updateHistoryButtons() {
    document.getElementById("undo").disabled = undoStack.length === 0;
    document.getElementById("redo").disabled = redoStack.length === 0;
  }

  function rememberBeforeMutation() {
    if (historySuspended || !doc) return;
    undoStack.push(clone(doc));
    if (undoStack.length > 50) undoStack.shift();
    redoStack = [];
    updateHistoryButtons();
  }

  function emitChange() {
    if (!doc || !editable) return;
    syncLayoutMetadata(doc);
    doc.editor_revision = finite(doc.editor_revision, 0) + 1;
    if (dirtyTimer) window.clearTimeout(dirtyTimer);
    dirtyTimer = window.setTimeout(function () {
      syncLayoutMetadata(doc);
      window.parent.postMessage({
        isStreamlitMessage:true,
        type:"streamlit:setComponentValue",
        value:{document:clone(doc),revision:doc.editor_revision}
      }, "*");
      setStatus("Draft synced to SURM session");
    }, 140);
  }

  function setStatus(message) {
    statusEl.textContent = message || "";
  }

  function makeId(prefix) {
    const used = new Set(allPlacements().map(function (x) { return x.id; }));
    let i = 1;
    let id = prefix + "-" + i;
    while (used.has(id)) {
      i += 1;
      id = prefix + "-" + i;
    }
    return id;
  }

  function makeNodeId(type) {
    const used = new Set((doc.library[type] || []).map(function (x) { return x.id; }));
    const prefix = type === "cause" ? "C" :
      type === "outcome" ? "O" :
      type === "preventativeBarrier" ? "PB" : "MB";
    let i = 1;
    let id = prefix + "_" + i;
    while (used.has(id)) {
      i += 1;
      id = prefix + "_" + i;
    }
    return id;
  }

  function defaultY(listLength) {
    return clamp(170 + listLength * 110, MIN_Y, MAX_Y);
  }

  function addObject(type) {
    rememberBeforeMutation();

    const nodeId = makeNodeId(type);
    const name = type === "cause" ? "New Threat" :
      type === "outcome" ? "New Consequence" :
      type === "preventativeBarrier" ? "New Preventive Barrier" :
      "New Mitigative Barrier";

    const node = {
      id: nodeId,
      type: type,
      name: name,
      description: "",
      surm_source: {type:"manual"},
    };

    if (type === "preventativeBarrier" || type === "mitigativeBarrier") {
      node.owner = "";
      node.effectiveness = "";
      node.degradation_factors = [];
      node.controls = [];
    }

    doc.library[type] = doc.library[type] || [];
    doc.library[type].push(node);

    const list = itemsFor(type);
    const placement = {
      id: makeId(
        type === "cause" ? "CAUSE-PLACEMENT" :
          type === "outcome" ? "OUTCOME-PLACEMENT" :
          type === "preventativeBarrier" ? "PREVENTIVE-PLACEMENT" :
          "MITIGATIVE-PLACEMENT"
      ),
      type: type,
      nodeId: nodeId,
      x: LANE_X[type],
      y: defaultY(list.length),
      w: (type === "cause" || type === "outcome") ? 240 : 150,
      h: (type === "cause" || type === "outcome") ? 86 : 110,
      pageId: "PAGE_1",
    };
    list.push(placement);

    if (type === "cause") {
      doc.lines.push({
        id: makeId("LINE-CAUSE"),
        originType: "cause",
        originId: placement.id,
        stops: [],
        pageId: "PAGE_1",
      });
    }
    if (type === "outcome") {
      doc.lines.push({
        id: makeId("LINE-OUTCOME"),
        originType: "outcome",
        originId: placement.id,
        stops: [],
        pageId: "PAGE_1",
      });
    }

    selected = {id: placement.id};
    emitChange();
    render();
    setStatus("Added " + name);
  }

  function removeSelected() {
    if (!selected || !doc) return false;
    const placement = placementForId(selected.id);
    if (!placement) return false;

    rememberBeforeMutation();

    const type = placement.type;
    const key = type === "cause" ? "causes" :
      type === "outcome" ? "outcomes" :
      type === "preventativeBarrier" ? "preventativeBarriers" :
      "mitigativeBarriers";

    const before = doc[key].length;
    doc[key] = doc[key].filter(function (p) { return p.id !== placement.id; });
    doc.library[type] = (doc.library[type] || []).filter(function (n) {
      return n.id !== placement.nodeId;
    });
    doc.lines = (doc.lines || [])
      .filter(function (line) { return line.originId !== placement.id; })
      .map(function (line) {
        return Object.assign({}, line, {
          stops: (line.stops || []).filter(function (stopId) {
            return stopId !== placement.id;
          }),
        });
      });

    selected = null;
    if (doc[key].length !== before) {
      emitChange();
      render();
      setStatus("Deleted " + type + " from the Bowtie draft");
      return true;
    }
    return false;
  }

  function evenlySpaced(count, min, max) {
    if (count <= 0) return [];
    if (count === 1) return [snap((min + max) / 2)];
    const step = (max - min) / (count - 1);
    return Array.from({length:count}, function (_, i) {
      return snap(min + i * step);
    });
  }

  function assignByTargets(barriers, targetYs) {
    const preferred = barriers.map(function (p) {
      const ys = targetYs(p);
      if (!ys.length) return finite(p.y, 450);
      return ys.reduce(function (sum, y) { return sum + y; }, 0) / ys.length;
    });

    const order = barriers
      .map(function (p, i) { return {p:p, preferred:preferred[i], i:i}; })
      .sort(function (a, b) {
        if (a.preferred !== b.preferred) return a.preferred - b.preferred;
        return a.p.id.localeCompare(b.p.id);
      });

    const positions = [];
    const minGap = 150;
    const maxY = MAX_Y;

    order.forEach(function (item, i) {
      let y = clamp(snap(item.preferred), MIN_Y, maxY);
      if (i > 0) y = Math.max(y, positions[i - 1] + minGap);
      positions.push(y);
    });

    if (positions.length && positions[positions.length - 1] > maxY) {
      const overflow = positions[positions.length - 1] - maxY;
      for (let i = 0; i < positions.length; i++) positions[i] -= overflow;
    }

    if (positions.length && positions[0] < MIN_Y) {
      const shift = MIN_Y - positions[0];
      for (let i = 0; i < positions.length; i++) positions[i] += shift;
    }

    order.forEach(function (item, i) {
      item.p.y = clamp(snap(positions[i]), MIN_Y, MAX_Y);
    });
  }

  function autoArrange() {
    if (!doc || !editable) return;
    rememberBeforeMutation();

    const causeYs = evenlySpaced(doc.causes.length, 180, 720);
    doc.causes.forEach(function (p, i) {
      p.x = LANE_X.cause;
      p.y = causeYs[i] || 450;
      p.w = 240; p.h = 86;
    });

    const outcomeYs = evenlySpaced(doc.outcomes.length, 180, 720);
    doc.outcomes.forEach(function (p, i) {
      p.x = LANE_X.outcome;
      p.y = outcomeYs[i] || 450;
      p.w = 240; p.h = 86;
    });

    const causeByPlacement = new Map(doc.causes.map(function (p) { return [p.id, p]; }));
    const outcomeByPlacement = new Map(doc.outcomes.map(function (p) { return [p.id, p]; }));

    const causeTargetYs = function (barrier) {
      return (doc.lines || []).filter(function (line) {
        return line.originType === "cause" && (line.stops || []).includes(barrier.id);
      }).map(function (line) {
        const origin = causeByPlacement.get(line.originId);
        return origin ? origin.y : null;
      }).filter(function (v) { return v != null; });
    };

    const outcomeTargetYs = function (barrier) {
      return (doc.lines || []).filter(function (line) {
        return line.originType === "outcome" && (line.stops || []).includes(barrier.id);
      }).map(function (line) {
        const origin = outcomeByPlacement.get(line.originId);
        return origin ? origin.y : null;
      }).filter(function (v) { return v != null; });
    };

    assignByTargets(doc.preventativeBarriers, causeTargetYs);
    assignByTargets(doc.mitigativeBarriers, outcomeTargetYs);

    doc.preventativeBarriers.forEach(function (p) {
      p.x = LANE_X.preventativeBarrier; p.w = 150; p.h = 110;
    });
    doc.mitigativeBarriers.forEach(function (p) {
      p.x = LANE_X.mitigativeBarrier; p.w = 150; p.h = 110;
    });

    syncLayoutMetadata(doc);
    emitChange();
    render();
    fitToContent(80, false);
    setStatus("Auto layout applied: relationships drive vertical placement");
  }

  function textWrap(text, maxChars, limit) {
    const value = String(text || "").trim();
    if (!value) return [""];
    const words = value.split(/\s+/).filter(Boolean);
    const out = [];
    let line = "";

    words.forEach(function (word) {
      const next = line ? line + " " + word : word;
      if (next.length > maxChars && line) {
        out.push(line);
        line = word;
      } else {
        line = next;
      }
    });
    if (line) out.push(line);
    if (out.length <= limit) return out;

    const clipped = out.slice(0, limit);
    clipped[limit - 1] = clipped[limit - 1].replace(/[\s.,;:]+$/, "") + "…";
    return clipped;
  }

  function createEl(name, attrs) {
    const el = document.createElementNS(NS, name);
    Object.keys(attrs || {}).forEach(function (key) {
      el.setAttribute(key, attrs[key]);
    });
    return el;
  }

  function groupForPlacement(p) {
    const g = createEl("g", {
      class:"node " + p.type,
      "data-id":p.id,
      "data-kind":p.type,
      "data-x":p.x,
      "data-y":p.y,
    });
    return g;
  }

  function renderCard(layer, p, kind) {
    const n = nodeFor(p);
    const g = groupForPlacement(p);
    const c = COLORS[kind];
    const rect = createEl("rect", {
      x:p.x - p.w / 2,
      y:p.y - p.h / 2,
      width:p.w,
      height:p.h,
      rx:10,
      fill:c.fill,
      stroke:c.stroke,
    });
    g.appendChild(rect);

    const labelLines = textWrap(n ? n.name : p.nodeId, 30, 4);
    labelLines.forEach(function (line, i) {
      const t = createEl("text", {
        x:p.x,
        y:p.y + (i - (labelLines.length - 1) / 2) * 18,
        "text-anchor":"middle",
        class:"node-label",
      });
      t.textContent = line;
      g.appendChild(t);
    });

    const meta = n && n.surm_management && n.surm_management.health
      ? String(n.surm_management.health)
      : "";
    if (meta) {
      const m = createEl("text", {
        x:p.x,
        y:p.y + p.h / 2 - 9,
        "text-anchor":"middle",
        class:"node-meta",
      });
      m.textContent = meta;
      g.appendChild(m);
    }

    applySelection(g, p.id);
    layer.appendChild(g);
    return g;
  }

  function renderBarrier(layer, p) {
    const n = nodeFor(p);
    const g = groupForPlacement(p);
    const c = COLORS[p.type];
    const rect = createEl("rect", {
      x:p.x - p.w / 2,
      y:p.y - p.h / 2,
      width:p.w,
      height:p.h,
      rx:8,
      fill:c.fill,
      stroke:c.stroke,
    });
    g.appendChild(rect);

    const labelLines = textWrap(n ? n.name : p.nodeId, 18, 5);
    labelLines.forEach(function (line, i) {
      const t = createEl("text", {
        x:p.x,
        y:p.y + (i - (labelLines.length - 1) / 2) * 15,
        "text-anchor":"middle",
        class:"barrier-label",
      });
      t.textContent = line;
      g.appendChild(t);
    });

    if (n && n.owner) {
      const owner = createEl("text", {
        x:p.x,
        y:p.y + p.h / 2 - 18,
        "text-anchor":"middle",
        class:"node-meta",
      });
      owner.textContent = "Owner: " + n.owner;
      g.appendChild(owner);
    }

    if (n && n.surm_management && n.surm_management.health) {
      const health = String(n.surm_management.health);
      const fill = health === "Healthy" ? "#2e7d32" :
        health === "At Risk" ? "#e65100" : "#607d8b";
      g.appendChild(createEl("circle", {
        cx:p.x + p.w / 2 - 12,
        cy:p.y - p.h / 2 + 12,
        r:6,
        fill:fill,
        class:"health-dot",
      }));
    }

    applySelection(g, p.id);
    layer.appendChild(g);
    return g;
  }

  function applySelection(g, id) {
    if (selected && selected.id === id) {
      g.classList.add("selected");
    }
  }

  function renderTopEvent(layer) {
    const event = doc.pages && doc.pages[0] && doc.pages[0].topLevelEvent
      ? doc.pages[0].topLevelEvent
      : {name:doc.name};

    const g = createEl("g", {"data-kind":"topLevelEvent", "data-id":"TLE_1"});
    const rect = createEl("rect", {
      x:665, y:375, width:270, height:150, rx:14, class:"event"
    });
    g.appendChild(rect);

    const kicker = createEl("text", {
      x:800, y:407, "text-anchor":"middle", class:"event-kicker"
    });
    kicker.textContent = "TOP EVENT";
    g.appendChild(kicker);

    const lines = textWrap(event.name || doc.name, 27, 4);
    lines.forEach(function (line, i) {
      const t = createEl("text", {
        x:800,
        y:447 + (i - (lines.length - 1) / 2) * 20,
        "text-anchor":"middle",
        class:"event-text",
      });
      t.textContent = line;
      g.appendChild(t);
    });

    layer.appendChild(g);
  }

  function createLane(layer, x, title, subtitle, fill, stroke) {
    const rect = createEl("rect", {
      x:x - 130,
      y:44,
      width:260,
      height:792,
      rx:14,
      class:"lane",
      fill:fill,
      stroke:stroke,
      "fill-opacity":"0.34",
    });
    layer.appendChild(rect);

    const t = createEl("text", {
      x:x, y:73, "text-anchor":"middle", class:"lane-title", fill:stroke
    });
    t.textContent = title;
    layer.appendChild(t);

    const s = createEl("text", {
      x:x, y:91, "text-anchor":"middle", class:"lane-subtitle"
    });
    s.textContent = subtitle;
    layer.appendChild(s);
  }

  function renderGrid(layer) {
    for (let x = 20; x < VIEW_W; x += GRID * 2) {
      for (let y = 100; y < VIEW_H; y += GRID * 2) {
        layer.appendChild(createEl("circle", {
          cx:x, cy:y, r:1.2, class:"grid-dot"
        }));
      }
    }
  }

  function renderConnectors(layer) {
    const drawnBarrierToEvent = new Set();
    const drawnEventToBarrier = new Set();

    (doc.lines || []).filter(function (line) {
      return line.originType === "cause";
    }).forEach(function (line, lineIndex) {
      const origin = placementForId(line.originId);
      if (!origin) return;

      const stops = (line.stops || [])
        .map(placementForId)
        .filter(function (p) { return p && p.type === "preventativeBarrier"; });

      if (!stops.length) {
        drawConnector(layer,
          {x:origin.x + origin.w / 2, y:origin.y},
          {x:665, y:450},
          "direct",
          lineIndex
        );
        return;
      }

      stops.forEach(function (barrier, stopIndex) {
        drawConnector(layer,
          {x:origin.x + origin.w / 2, y:origin.y},
          {x:barrier.x - barrier.w / 2, y:barrier.y},
          "cause",
          lineIndex * 17 + stopIndex
        );

        if (!drawnBarrierToEvent.has(barrier.id)) {
          drawnBarrierToEvent.add(barrier.id);
          drawConnector(
            layer,
            {x:barrier.x + barrier.w / 2, y:barrier.y},
            {x:665, y:450},
            "cause secondary",
            stopIndex + 31
          );
        }
      });
    });

    (doc.lines || []).filter(function (line) {
      return line.originType === "outcome";
    }).forEach(function (line, lineIndex) {
      const origin = placementForId(line.originId);
      if (!origin) return;

      const stops = (line.stops || [])
        .map(placementForId)
        .filter(function (p) { return p && p.type === "mitigativeBarrier"; });

      if (!stops.length) {
        drawConnector(layer,
          {x:935, y:450},
          {x:origin.x - origin.w / 2, y:origin.y},
          "direct",
          lineIndex
        );
        return;
      }

      stops.forEach(function (barrier, stopIndex) {
        if (!drawnEventToBarrier.has(barrier.id)) {
          drawnEventToBarrier.add(barrier.id);
          drawConnector(
            layer,
            {x:935, y:450},
            {x:barrier.x - barrier.w / 2, y:barrier.y},
            "mitigate secondary",
            stopIndex + 51
          );
        }

        drawConnector(layer,
          {x:barrier.x + barrier.w / 2, y:barrier.y},
          {x:origin.x - origin.w / 2, y:origin.y},
          "mitigate",
          lineIndex * 17 + stopIndex
        );
      });
    });
  }

  function drawConnector(layer, from, to, className, offsetIndex) {
    const leftSide = to.x >= from.x;
    const direction = leftSide ? 1 : -1;
    const separation = 18 + ((offsetIndex || 0) % 3) * 10;
    const mid = from.x + direction * (Math.abs(to.x - from.x) * 0.48 + separation);
    const d = "M " + from.x + " " + from.y +
      " L " + mid + " " + from.y +
      " L " + mid + " " + to.y +
      " L " + to.x + " " + to.y;

    const path = createEl("path", {
      d:d,
      class:"connector " + className,
      "marker-end":"url(#arrowhead)",
      "data-from-x":from.x,
      "data-from-y":from.y,
      "data-to-x":to.x,
      "data-to-y":to.y,
    });
    layer.appendChild(path);
  }

  function render() {
    if (!doc) return;

    svg.innerHTML = "";

    const defs = createEl("defs", {});
    defs.innerHTML =
      '<marker id="arrowhead" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">' +
      '<polygon points="0 0,9 3.5,0 7" fill="#72827a"></polygon></marker>';
    svg.appendChild(defs);

    const bg = createEl("rect", {
      x:0, y:0, width:VIEW_W, height:VIEW_H, fill:"#fbfdfb"
    });
    bg.setAttribute("data-canvas-bg", "1");
    svg.appendChild(bg);

    const gridLayer = createEl("g", {"data-layer":"grid"});
    renderGrid(gridLayer);
    svg.appendChild(gridLayer);

    const lanes = createEl("g", {"data-layer":"lanes"});
    createLane(lanes, LANE_X.cause, "THREATS", "Causes / initiating conditions", "#f7e8c5", "#b57a17");
    createLane(lanes, LANE_X.preventativeBarrier, "PREVENTIVE", "Controls before the top event", "#e5f4ec", "#168a62");
    createLane(lanes, LANE_X.topLevelEvent, "TOP EVENT", "Central undesired event", "#fbe9ea", "#b51218");
    createLane(lanes, LANE_X.mitigativeBarrier, "MITIGATIVE", "Controls after the top event", "#ece9fb", "#564ab5");
    createLane(lanes, LANE_X.outcome, "CONSEQUENCES", "Potential outcomes", "#f8e4dc", "#a84c2f");
    svg.appendChild(lanes);

    const connectors = createEl("g", {"data-layer":"connectors"});
    renderConnectors(connectors);
    svg.appendChild(connectors);

    const nodes = createEl("g", {"data-layer":"nodes"});
    doc.causes.forEach(function (p) { renderCard(nodes, p, "cause"); });
    doc.preventativeBarriers.forEach(function (p) { renderBarrier(nodes, p); });
    renderTopEvent(nodes);
    doc.mitigativeBarriers.forEach(function (p) { renderBarrier(nodes, p); });
    doc.outcomes.forEach(function (p) { renderCard(nodes, p, "outcome"); });
    svg.appendChild(nodes);

    const focus = createEl("rect", {
      x:649, y:365, width:302, height:170, rx:16, class:"focus-ring"
    });
    svg.appendChild(focus);

    bindNodeEvents();
    renderObjects();
    renderEditor();
    renderRelationships();
    renderHealth();

    document.getElementById("title").textContent = doc.name || "SURM Bowtie";
    document.getElementById("riskInfo").innerHTML =
      '<span class="badge">' + esc(doc.risk_id || "NEW") + "</span> " + esc(doc.name || "");
    document.getElementById("delete").disabled = !selected || !editable;
    zoomResetEl.textContent = Math.round((VIEW_W / camera.w) * 100) + "%";
    applyCamera();
  }

  function renderObjects() {
    const groups = [
      ["cause", "Threats"],
      ["preventativeBarrier", "Preventive barriers"],
      ["mitigativeBarrier", "Mitigative barriers"],
      ["outcome", "Consequences"],
    ];

    objectsEl.innerHTML = groups.map(function (entry) {
      const type = entry[0];
      const title = entry[1];
      const list = itemsFor(type);

      const header = '<div class="small" style="font-weight:700;margin:5px 0 3px">' +
        title + " · " + list.length + "</div>";

      const buttons = list.length
        ? list.map(function (p) {
          const n = nodeFor(p);
          const active = selected && selected.id === p.id ? " active" : "";
          return '<button class="' + active + '" data-p="' + esc(p.id) + '">' +
            esc(n ? n.name : p.nodeId) + "</button>";
        }).join("")
        : '<div class="small" style="padding:2px 0 5px">None</div>';

      return header + buttons;
    }).join("");

    objectsEl.querySelectorAll("button[data-p]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        selected = {id:btn.getAttribute("data-p")};
        render();
      });
    });
  }

  function renderEditor() {
    const p = selected ? placementForId(selected.id) : null;
    if (!p) {
      editorEl.innerHTML = '<div class="small">Select a node on the canvas or Navigator.</div>';
      return;
    }

    const n = nodeFor(p);
    if (!n) {
      editorEl.innerHTML = '<div class="small">Selected node data is unavailable.</div>';
      return;
    }

    if (!editable) {
      editorEl.innerHTML = '<div class="small">Read-only reporting view.</div>';
      return;
    }

    let html =
      '<div class="field"><label>Name</label><input id="editName" value="' + esc(n.name) + '"></div>' +
      '<div class="field"><label>Description</label><textarea id="editDesc">' + esc(n.description || "") + "</textarea></div>";

    if (p.type === "preventativeBarrier" || p.type === "mitigativeBarrier") {
      html +=
        '<div class="field"><label>Owner</label><input id="editOwner" value="' + esc(n.owner || "") + '"></div>' +
        '<div class="field"><label>Effectiveness</label><select id="editEff">' +
          '<option value=""></option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>' +
        '</select></div>' +
        '<div class="field"><label>Degradation factors</label><textarea id="editDegradation">' +
          esc((n.degradation_factors || []).join("\n")) + "</textarea></div>" +
        '<div class="field"><label>Controls</label><textarea id="editControls">' +
          esc((n.controls || []).join("\n")) + "</textarea></div>";
    }

    html +=
      '<div class="small" style="margin-top:7px">Lane: ' + esc(p.type) +
      " · Position snaps to " + GRID + " px vertically.</div>" +
      '<button id="selectConnections" class="inspector-action">Show connections</button>';

    editorEl.innerHTML = html;

    const eff = document.getElementById("editEff");
    if (eff) eff.value = n.effectiveness || "";

    [
      "editName","editDesc","editOwner","editEff","editDegradation","editControls"
    ].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener("change", function () {
        rememberBeforeMutation();
        const current = nodeFor(p);
        if (!current) return;

        current.name = document.getElementById("editName").value;
        current.description = document.getElementById("editDesc").value;

        const owner = document.getElementById("editOwner");
        if (owner) current.owner = owner.value;

        const effectiveness = document.getElementById("editEff");
        if (effectiveness) current.effectiveness = effectiveness.value;

        const degradation = document.getElementById("editDegradation");
        if (degradation) {
          current.degradation_factors = degradation.value
            .split(/\n/)
            .map(function (x) { return x.trim(); })
            .filter(Boolean);
        }

        const controls = document.getElementById("editControls");
        if (controls) {
          current.controls = controls.value
            .split(/\n/)
            .map(function (x) { return x.trim(); })
            .filter(Boolean);
        }

        emitChange();
        render();
      });
    });

    const selectConnections = document.getElementById("selectConnections");
    if (selectConnections) {
      selectConnections.addEventListener("click", function () {
        const origin = p.type === "cause" || p.type === "outcome"
          ? p
          : null;
        if (origin) {
          renderRelationships();
        } else {
          setStatus("Select a Threat or Consequence to edit relationship links");
        }
      });
    }
  }

  function renderRelationships() {
    const p = selected ? placementForId(selected.id) : null;
    if (!p || !["cause", "outcome"].includes(p.type)) {
      relationshipsEl.innerHTML =
        '<div class="small">Select a threat or consequence to manage its barrier links.</div>';
      return;
    }

    const line = lineForOrigin(p.id);
    if (!line) {
      relationshipsEl.innerHTML = '<div class="small">No relationship record exists.</div>';
      return;
    }

    if (!editable) {
      relationshipsEl.innerHTML = '<div class="small">Read-only reporting view.</div>';
      return;
    }

    const barrierType = p.type === "cause"
      ? "preventativeBarrier"
      : "mitigativeBarrier";
    const barriers = itemsFor(barrierType);
    const stopSet = new Set(line.stops || []);

    const header = '<div class="small" style="margin-bottom:7px">Links for <strong>' +
      esc(nodeFor(p)?.name || p.nodeId) + "</strong></div>";

    const rows = barriers.map(function (b) {
      const n = nodeFor(b);
      return '<div class="link-row">' +
        '<input type="checkbox" data-rel="' + esc(b.id) + '"' +
        (stopSet.has(b.id) ? " checked" : "") + ">' +
        '<span class="link-name">' + esc(n ? n.name : b.nodeId) + "</span>" +
        (n && n.owner ? '<span class="connection-chip">' + esc(n.owner) + "</span>" : "") +
        "</div>";
    }).join("");

    relationshipsEl.innerHTML =
      header +
      (rows || '<div class="small">No compatible barriers exist yet.</div>') +
      '<div class="small" style="margin-top:7px">A shared barrier is rendered once and can serve multiple relationships.</div>';

    relationshipsEl.querySelectorAll("input[data-rel]").forEach(function (cb) {
      cb.addEventListener("change", function () {
        rememberBeforeMutation();
        const id = cb.getAttribute("data-rel");
        line.stops = Array.isArray(line.stops) ? line.stops : [];

        if (cb.checked) {
          if (!line.stops.includes(id)) line.stops.push(id);
        } else {
          line.stops = line.stops.filter(function (x) { return x !== id; });
        }

        emitChange();
        render();
      });
    });
  }

  function renderHealth() {
    const barrierPlacements = [
      ...doc.preventativeBarriers,
      ...doc.mitigativeBarriers,
    ];
    const unowned = barrierPlacements.filter(function (p) {
      const n = nodeFor(p);
      return !(n && String(n.owner || "").trim());
    }).length;

    const linked = new Set(
      (doc.lines || []).reduce(function (acc, line) {
        (line.stops || []).forEach(function (id) { acc.add(id); });
        return acc;
      }, [])
    );
    const unlinked = barrierPlacements.filter(function (p) {
      return !linked.has(p.id);
    }).length;

    const chips = [
      '<span class="health-chip ok">✓ ' + doc.causes.length + " threats</span>",
      '<span class="health-chip ok">✓ ' + doc.preventativeBarriers.length + " preventive</span>",
      '<span class="health-chip">• ' + doc.mitigativeBarriers.length + " mitigative</span>",
      '<span class="health-chip">• ' + doc.outcomes.length + " consequences</span>",
    ];

    if (unowned) {
      chips.push('<span class="health-chip warn">⚠ ' + unowned + " barrier" + (unowned === 1 ? "" : "s") + " missing owner</span>");
    }
    if (unlinked) {
      chips.push('<span class="health-chip warn">⚠ ' + unlinked + " unlinked barrier" + (unlinked === 1 ? "" : "s") + "</span>");
    }

    healthEl.innerHTML = chips.join("");
  }

  function nodeGroup(id) {
    return svg.querySelector('.node[data-id="' + cssEscape(id) + '"]');
  }

  function cssEscape(value) {
    return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }

  function bindNodeEvents() {
    svg.querySelectorAll(".node").forEach(function (el) {
      el.addEventListener("click", function (event) {
        event.stopPropagation();
        if (dragState && dragState.moved) return;
        const id = el.getAttribute("data-id");
        selected = {id:id};
        render();
      });

      el.addEventListener("pointerdown", function (event) {
        if (!editable) return;
        event.stopPropagation();

        const p = placementForId(el.getAttribute("data-id"));
        if (!p) return;

        const scene = screenToScene(event.clientX, event.clientY);
        dragState = {
          id:p.id,
          element:el,
          originX:p.x,
          originY:p.y,
          startSceneX:scene.x,
          startSceneY:scene.y,
          moved:false,
          historyRecorded:false,
        };

        selected = {id:p.id};
        el.setPointerCapture(event.pointerId);
      });

      el.addEventListener("pointermove", function (event) {
        if (!dragState || dragState.id !== el.getAttribute("data-id")) return;

        const scene = screenToScene(event.clientX, event.clientY);
        let nextX = dragState.originX + (scene.x - dragState.startSceneX);
        let nextY = dragState.originY + (scene.y - dragState.startSceneY);

        if (pinnedLane(pTypeOf(el))) {
          nextX = LANE_X[pTypeOf(el)];
        } else {
          nextX = snap(nextX);
        }
        nextY = clamp(snap(nextY), MIN_Y, MAX_Y);

        const p = placementForId(dragState.id);
        if (!p) return;

        const changed = p.x !== nextX || p.y !== nextY;
        if (!changed) return;

        if (!dragState.historyRecorded) {
          rememberBeforeMutation();
          dragState.historyRecorded = true;
        }

        p.x = nextX;
        p.y = nextY;
        dragState.moved = true;

        const dx = p.x - dragState.originX;
        const dy = p.y - dragState.originY;
        el.setAttribute("transform", "translate(" + dx + " " + dy + ")");
        el.setAttribute("data-x", p.x);
        el.setAttribute("data-y", p.y);
        refreshConnectorLayer();

        setStatus("Dragging · lane locked · " + GRID + " px snap");
      });

      el.addEventListener("pointerup", function (event) {
        if (!dragState || dragState.id !== el.getAttribute("data-id")) return;

        try {
          el.releasePointerCapture(event.pointerId);
        } catch (_) {}

        const moved = dragState.moved;
        dragState = null;

        if (moved) {
          syncLayoutMetadata(doc);
          emitChange();
          render();
          setStatus("Position saved to Bowtie draft");
        }
      });
    });
  }

  function pTypeOf(el) {
    return el.getAttribute("data-kind");
  }

  function pinnedLane(type) {
    return type === "cause" ||
      type === "preventativeBarrier" ||
      type === "mitigativeBarrier" ||
      type === "outcome";
  }

  function refreshConnectorLayer() {
    const existing = svg.querySelector('[data-layer="connectors"]');
    if (!existing) return;
    existing.innerHTML = "";
    renderConnectors(existing);
  }

  function screenToScene(clientX, clientY) {
    const rect = svg.getBoundingClientRect();
    return {
      x: camera.x + ((clientX - rect.left) / rect.width) * camera.w,
      y: camera.y + ((clientY - rect.top) / rect.height) * camera.h,
    };
  }

  function applyCamera() {
    camera.x = clamp(camera.x, 0, VIEW_W - camera.w);
    camera.y = clamp(camera.y, 0, VIEW_H - camera.h);
    svg.setAttribute(
      "viewBox",
      [camera.x, camera.y, camera.w, camera.h].map(function (n) {
        return Math.round(n * 10) / 10;
      }).join(" ")
    );
    zoomResetEl.textContent = Math.round((VIEW_W / camera.w) * 100) + "%";
  }

  function setZoom(factor, centerX, centerY) {
    const nextW = clamp(camera.w / factor, 600, VIEW_W);
    const nextH = nextW * VIEW_H / VIEW_W;
    const cx = centerX == null ? camera.x + camera.w / 2 : centerX;
    const cy = centerY == null ? camera.y + camera.h / 2 : centerY;
    const ratio = nextW / camera.w;

    camera.x = cx - (cx - camera.x) * ratio;
    camera.y = cy - (cy - camera.y) * (nextH / camera.h);
    camera.w = nextW;
    camera.h = nextH;
    applyCamera();
  }

  function zoomAtCursor(factor, event) {
    const point = screenToScene(event.clientX, event.clientY);
    setZoom(factor, point.x, point.y);
  }

  function resetZoom() {
    camera = {x:0, y:0, w:VIEW_W, h:VIEW_H};
    applyCamera();
  }

  function fitToContent(padding, announce) {
    const points = [{x:800, y:450, w:270, h:150}]
      .concat(allPlacements().map(function (p) {
        return {x:p.x, y:p.y, w:p.w, h:p.h};
      }));

    if (!points.length) return;

    const left = Math.min.apply(null, points.map(function (p) { return p.x - p.w / 2; }));
    const right = Math.max.apply(null, points.map(function (p) { return p.x + p.w / 2; }));
    const top = Math.min.apply(null, points.map(function (p) { return p.y - p.h / 2; }));
    const bottom = Math.max.apply(null, points.map(function (p) { return p.y + p.h / 2; }));

    const pad = finite(padding, 70);
    const width = clamp(right - left + pad * 2, 680, VIEW_W);
    const height = clamp(bottom - top + pad * 2, 500, VIEW_H);
    const aspect = VIEW_W / VIEW_H;

    let w = width;
    let h = height;
    if (w / h > aspect) h = w / aspect;
    else w = h * aspect;

    camera.w = clamp(w, 600, VIEW_W);
    camera.h = clamp(h, camera.w * VIEW_H / VIEW_W, VIEW_H);
    camera.x = clamp(((left + right) / 2) - camera.w / 2, 0, VIEW_W - camera.w);
    camera.y = clamp(((top + bottom) / 2) - camera.h / 2, 0, VIEW_H - camera.h);

    applyCamera();
    if (announce !== false) setStatus("Fit to content");
  }

  svg.addEventListener("pointerdown", function (event) {
    if (!editable) return;
    if (event.target.closest && event.target.closest(".node")) return;

    panState = {
      startClientX:event.clientX,
      startClientY:event.clientY,
      originX:camera.x,
      originY:camera.y,
      pointerId:event.pointerId,
    };
    svg.setPointerCapture(event.pointerId);
    svg.style.cursor = "grabbing";
  });

  svg.addEventListener("pointermove", function (event) {
    if (!panState) return;
    const rect = svg.getBoundingClientRect();
    camera.x = panState.originX - ((event.clientX - panState.startClientX) / rect.width) * camera.w;
    camera.y = panState.originY - ((event.clientY - panState.startClientY) / rect.height) * camera.h;
    applyCamera();
  });

  svg.addEventListener("pointerup", function (event) {
    if (!panState) return;
    try { svg.releasePointerCapture(event.pointerId); } catch (_) {}
    panState = null;
    svg.style.cursor = "";
  });

  svg.addEventListener("click", function (event) {
    if (event.target.getAttribute && event.target.getAttribute("data-canvas-bg") === "1") {
      selected = null;
      render();
    }
  });

  svg.addEventListener("wheel", function (event) {
    event.preventDefault();
    zoomAtCursor(event.deltaY < 0 ? 1.12 : 0.89, event);
  }, {passive:false});

  function undoChange() {
    if (!doc || !undoStack.length || !editable) return;
    const previous = undoStack.pop();
    redoStack.push(clone(doc));
    historySuspended = true;
    doc = normalizeDocument(previous);
    historySuspended = false;
    emitChange();
    render();
    updateHistoryButtons();
    setStatus("Undo");
  }

  function redoChange() {
    if (!doc || !redoStack.length || !editable) return;
    const next = redoStack.pop();
    undoStack.push(clone(doc));
    historySuspended = true;
    doc = normalizeDocument(next);
    historySuspended = false;
    emitChange();
    render();
    updateHistoryButtons();
    setStatus("Redo");
  }

  function exportSvg() {
    if (!doc) return;
    const cloneSvg = svg.cloneNode(true);
    cloneSvg.setAttribute("xmlns", NS);
    cloneSvg.setAttribute("viewBox", "0 0 " + VIEW_W + " " + VIEW_H);
    cloneSvg.removeAttribute("aria-label");
    const source =
      '<?xml version="1.0" encoding="UTF-8"?>\n' +
      new XMLSerializer().serializeToString(cloneSvg);
    const blob = new Blob([source], {type:"image/svg+xml;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = doc.risk_id
      ? "SURM_" + doc.risk_id + "_Bowtie_V2.svg"
      : "SURM_Bowtie_V2.svg";
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportPng() {
    if (!doc) return;

    const cloneSvg = svg.cloneNode(true);
    cloneSvg.setAttribute("xmlns", NS);
    cloneSvg.setAttribute("viewBox", "0 0 " + VIEW_W + " " + VIEW_H);
    const source = new XMLSerializer().serializeToString(cloneSvg);
    const blob = new Blob([source], {type:"image/svg+xml;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const image = new Image();

    image.onload = function () {
      const canvas = document.createElement("canvas");
      canvas.width = 3200;
      canvas.height = 1800;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);

      canvas.toBlob(function (png) {
        if (!png) return;
        const pngUrl = URL.createObjectURL(png);
        const a = document.createElement("a");
        a.href = pngUrl;
        a.download = doc.risk_id
          ? "SURM_" + doc.risk_id + "_Bowtie_V2.png"
          : "SURM_Bowtie_V2.png";
        a.click();
        URL.revokeObjectURL(pngUrl);
      }, "image/png");
    };
    image.src = url;
  }

  document.getElementById("auto").addEventListener("click", autoArrange);
  document.getElementById("fit").addEventListener("click", function () { fitToContent(80); });
  document.getElementById("zoomOut").addEventListener("click", function () { setZoom(0.88); });
  document.getElementById("zoomIn").addEventListener("click", function () { setZoom(1.14); });
  document.getElementById("zoomReset").addEventListener("click", resetZoom);
  document.getElementById("undo").addEventListener("click", undoChange);
  document.getElementById("redo").addEventListener("click", redoChange);
  document.getElementById("addCause").addEventListener("click", function () { addObject("cause"); });
  document.getElementById("addPrevent").addEventListener("click", function () { addObject("preventativeBarrier"); });
  document.getElementById("addMitigate").addEventListener("click", function () { addObject("mitigativeBarrier"); });
  document.getElementById("addOutcome").addEventListener("click", function () { addObject("outcome"); });
  document.getElementById("delete").addEventListener("click", removeSelected);
  document.getElementById("exportSvg").addEventListener("click", exportSvg);
  document.getElementById("exportPng").addEventListener("click", exportPng);

  window.addEventListener("message", function (event) {
    const data = event.data || {};
    if (data.type !== "streamlit:render") return;

    args = data.args || {};
    editable = args.editable !== false;

    ["addCause","addPrevent","addMitigate","addOutcome","delete"].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.style.display = editable ? "inline-block" : "none";
    });

    const incoming = args.document;
    if (incoming) {
      if (!doc || finite(incoming.editor_revision, 0) >= finite(doc.editor_revision, 0)) {
        doc = normalizeDocument(incoming);
        undoStack = [];
        redoStack = [];
        selected = null;
        render();
      }
    }

    window.setTimeout(function () { ready(args.height); }, 0);
  });

  ready(820);
})();