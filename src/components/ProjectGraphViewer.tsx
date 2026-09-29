import React, { useEffect, useRef, useState, useMemo, useCallback } from "react";
import {
  Share2, Search, Filter, RefreshCw, ZoomIn, ZoomOut, Maximize2, Minimize2,
  Info, Tag
} from "lucide-react";

export interface GraphNodeData {
  id: number | string;
  name: string;
  type: string;
  degree?: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphLinkData {
  source: number | string;
  target: number | string;
  relationship: string;
  confidence?: number;
}

interface ProjectGraphViewerProps {
  nodes: GraphNodeData[];
  links: GraphLinkData[];
  onNodeClick?: (node: GraphNodeData) => void;
  isLoading?: boolean;
  onRefresh?: () => void;
  /** Names (lowercased) of shared entities to highlight with a golden glow */
  highlightNames?: Set<string>;
  /** Accent color used for edges and selected UI elements */
  accentColor?: string;
}

const TYPE_COLORS: Record<string, { bg: string; text: string; border: string; colorHex: string }> = {
  Project:     { bg: "bg-indigo-900/60", text: "text-indigo-200", border: "border-indigo-500", colorHex: "#6366f1" },
  Domain:      { bg: "bg-purple-900/60", text: "text-purple-200", border: "border-purple-500", colorHex: "#a855f7" },
  Subdomain:   { bg: "bg-fuchsia-900/60", text: "text-fuchsia-200", border: "border-fuchsia-500", colorHex: "#d946ef" },
  Algorithm:   { bg: "bg-cyan-900/60",   text: "text-cyan-200",   border: "border-cyan-500",   colorHex: "#06b6d4" },
  Technology:  { bg: "bg-emerald-900/60",text: "text-emerald-200",border: "border-emerald-500",colorHex: "#10b981" },
  Framework:   { bg: "bg-teal-900/60",   text: "text-teal-200",   border: "border-teal-500",   colorHex: "#14b8a6" },
  Library:     { bg: "bg-sky-900/60",    text: "text-sky-200",    border: "border-sky-500",    colorHex: "#0ea5e9" },
  Dataset:     { bg: "bg-amber-900/60",  text: "text-amber-200",  border: "border-amber-500",  colorHex: "#f59e0b" },
  Application: { bg: "bg-rose-900/60",   text: "text-rose-200",   border: "border-rose-500",   colorHex: "#f43f5e" },
  Hardware:    { bg: "bg-pink-900/60",   text: "text-pink-200",   border: "border-pink-500",   colorHex: "#ec4899" },
  Metric:      { bg: "bg-slate-800",      text: "text-slate-200",  border: "border-slate-500",  colorHex: "#94a3b8" },
};

const ALL_NODE_TYPES = [
  "Project", "Domain", "Subdomain", "Algorithm", "Technology",
  "Framework", "Library", "Dataset", "Application", "Hardware", "Metric"
];

export const ProjectGraphViewer: React.FC<ProjectGraphViewerProps> = ({
  nodes,
  links,
  onNodeClick,
  isLoading = false,
  onRefresh,
  highlightNames,
  accentColor = '#6366f1',
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  // All render-time values in refs to avoid stale closures
  const panOffsetRef = useRef({ x: 0, y: 0 });
  const zoomLevelRef = useRef(1);
  const searchTermRef = useRef("");
  const selectedNodeRef = useRef<GraphNodeData | null>(null);
  const draggedNodeRef = useRef<GraphNodeData | null>(null);
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const ticksRef = useRef(0);
  const simLoopRef = useRef<number>(0);
  const userInteractedRef = useRef(false);

  // React state (for UI re-renders only)
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTypes, setActiveTypes] = useState<Set<string>>(new Set(ALL_NODE_TYPES));
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Normalize all node IDs to strings for robust map & set lookups
  const normalizedNodes = useMemo(() => nodes.map(n => ({ ...n, id: String(n.id) })), [nodes]);
  const normalizedLinks = useMemo(() => links.map(l => ({ ...l, source: String(l.source), target: String(l.target) })), [links]);

  const filteredNodes = useMemo(() => normalizedNodes.filter(n => activeTypes.has(n.type)), [normalizedNodes, activeTypes]);
  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map(n => n.id)), [filteredNodes]);
  const filteredLinks = useMemo(() => normalizedLinks.filter(l => filteredNodeIds.has(l.source) && filteredNodeIds.has(l.target)), [normalizedLinks, filteredNodeIds]);

  const filteredLinksRef = useRef(filteredLinks);
  useEffect(() => { filteredLinksRef.current = filteredLinks; }, [filteredLinks]);

  const simulationNodesRef = useRef<Map<string, GraphNodeData>>(new Map());
  // Store highlightNames and accentColor in refs for stale-closure-safe access in renderCanvas
  const highlightNamesRef = useRef<Set<string> | undefined>(highlightNames);
  const accentColorRef = useRef<string>(accentColor);
  useEffect(() => { highlightNamesRef.current = highlightNames; }, [highlightNames]);
  useEffect(() => { accentColorRef.current = accentColor; }, [accentColor]);

  // Resize canvas with devicePixelRatio support for crispness
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const dpr = window.devicePixelRatio || 1;
    const w = container.clientWidth;
    const h = container.clientHeight;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
  }, []);

  // Core render — reads ONLY from refs, never from captured state
  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    // Guard: canvas must have real dimensions. If 0, the container hasn't been
    // laid out yet — size it immediately before drawing.
    if (canvas.width === 0 || canvas.height === 0) {
      const container = containerRef.current;
      if (!container) return;
      const dpr2 = window.devicePixelRatio || 1;
      const w2 = container.clientWidth || 900;
      const h2 = container.clientHeight || 600;
      canvas.width = Math.round(w2 * dpr2);
      canvas.height = Math.round(h2 * dpr2);
      canvas.style.width = w2 + 'px';
      canvas.style.height = h2 + 'px';
      if (canvas.width === 0 || canvas.height === 0) return; // Still 0, nothing to draw
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.scale(dpr, dpr);
    ctx.translate(panOffsetRef.current.x, panOffsetRef.current.y);
    ctx.scale(zoomLevelRef.current, zoomLevelRef.current);

    const simMap = simulationNodesRef.current;
    const currentLinks = filteredLinksRef.current;

    // Draw edges
    currentLinks.forEach(link => {
      const src = simMap.get(String(link.source));
      const tgt = simMap.get(String(link.target));
      if (!src || !tgt) return;
      const sx = src.x ?? 0, sy = src.y ?? 0;
      const tx = tgt.x ?? 0, ty = tgt.y ?? 0;
      if (!isFinite(sx) || !isFinite(sy) || !isFinite(tx) || !isFinite(ty)) return;
      if (sx === 0 && sy === 0 && tx === 0 && ty === 0) return;
      const isCoOccur = link.relationship === "CO_OCCURS";
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(tx, ty);
      ctx.strokeStyle = isCoOccur ? "rgba(148,163,184,0.55)" : `${accentColorRef.current}cc`;
      ctx.lineWidth = isCoOccur ? 1.2 : 2.2;
      ctx.setLineDash(isCoOccur ? [4, 4] : []);
      ctx.stroke();
    });
    ctx.setLineDash([]);

    // Draw nodes
    const lowerSearch = searchTermRef.current.trim().toLowerCase();
    const selected = selectedNodeRef.current;
    const dragged = draggedNodeRef.current;

    Array.from(simMap.values()).forEach(node => {
      const nx = node.x ?? 0, ny = node.y ?? 0;
      if (!isFinite(nx) || !isFinite(ny)) return;
      if (nx === 0 && ny === 0) return;
      const isSearch = lowerSearch.length > 0 && node.name.toLowerCase().includes(lowerSearch);
      const isSel = selected && String(selected.id) === String(node.id);
      const isDrag = dragged && String(dragged.id) === String(node.id);
      const isShared = !!(highlightNamesRef.current && highlightNamesRef.current.has(node.name?.toLowerCase().trim()));
      const style = TYPE_COLORS[node.type] || TYPE_COLORS["Metric"];
      const r = node.type === "Project" ? 16 : Math.min(13, 7 + (node.degree || 1));

      // Shared entity — golden glow
      if (isShared) {
        ctx.beginPath();
        ctx.arc(nx, ny, r + 8, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(234,179,8,0.35)";
        ctx.fill();
      }

      if (isSel || isSearch || isDrag) {
        ctx.beginPath();
        ctx.arc(nx, ny, r + (isDrag ? 10 : 7), 0, 2 * Math.PI);
        ctx.fillStyle = isSel || isDrag ? "rgba(99,102,241,0.28)" : "rgba(234,179,8,0.25)";
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(nx, ny, r, 0, 2 * Math.PI);
      ctx.fillStyle = style.colorHex;
      ctx.fill();
      ctx.lineWidth = isSel || isDrag ? 2.5 : 1.2;
      ctx.strokeStyle = isSel || isDrag ? "#fff" : "rgba(255,255,255,0.45)";
      ctx.stroke();

      const isHi = isSel || isSearch || isDrag;
      const maxCh = isHi ? 22 : 14;
      const label = node.name.length > maxCh ? node.name.substring(0, maxCh - 1) + "…" : node.name;
      ctx.font = (isHi ? "bold " : "") + (isHi ? "11" : "9") + "px Inter, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      const ly = ny + r + 5;
      ctx.lineWidth = 4;
      ctx.strokeStyle = "rgba(2,6,23,0.92)";
      ctx.strokeText(label, nx, ly);
      ctx.fillStyle = isHi ? "#fff" : "rgba(203,213,225,0.9)";
      ctx.fillText(label, nx, ly);
    });

    ctx.restore();
  }, []);

  // Fit all nodes into canvas view
  const fitToView = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    const cw = container.clientWidth || 900;
    const ch = container.clientHeight || 600;
    const simNodes = Array.from(simulationNodesRef.current.values());
    if (simNodes.length === 0) {
      panOffsetRef.current = { x: 0, y: 0 };
      zoomLevelRef.current = 1;
      setZoomLevel(1);
      renderCanvas();
      return;
    }
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    simNodes.forEach(n => {
      const x = n.x ?? 0, y = n.y ?? 0;
      if (isFinite(x) && isFinite(y) && (x !== 0 || y !== 0)) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    });
    if (!isFinite(minX) || minX === Infinity) return;
    const gw = Math.max(60, maxX - minX);
    const gh = Math.max(60, maxY - minY);
    const padding = 70;
    const scaleX = (cw - padding * 2) / gw;
    const scaleY = (ch - padding * 2) / gh;
    const targetZoom = Math.min(2.0, Math.max(0.3, Math.min(scaleX, scaleY)));
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const targetPanX = cw / 2 - centerX * targetZoom;
    const targetPanY = ch / 2 - centerY * targetZoom;
    panOffsetRef.current = { x: targetPanX, y: targetPanY };
    zoomLevelRef.current = targetZoom;
    setZoomLevel(targetZoom);
    renderCanvas();
  }, [renderCanvas]);

  // Physics simulation
  useEffect(() => {
    cancelAnimationFrame(simLoopRef.current);
    const simMap = simulationNodesRef.current;
    const container = containerRef.current;
    const width = container?.clientWidth || 900;
    const height = container?.clientHeight || 600;

    filteredNodes.forEach((node, i) => {
      const nid = String(node.id);
      if (!simMap.has(nid)) {
        const angle = (i / Math.max(1, filteredNodes.length)) * 2 * Math.PI;
        const rad = Math.min(width, height) * 0.28 * (0.5 + Math.random() * 0.5);
        simMap.set(nid, { ...node, id: nid, x: width / 2 + rad * Math.cos(angle), y: height / 2 + rad * Math.sin(angle), vx: 0, vy: 0 });
      } else {
        const ex = simMap.get(nid)!;
        ex.name = node.name; ex.type = node.type; ex.degree = node.degree;
      }
    });
    const activeIds = new Set(filteredNodes.map(n => String(n.id)));
    Array.from(simMap.keys()).forEach(id => { if (!activeIds.has(String(id))) simMap.delete(id); });

    ticksRef.current = 0;
    const MAX = 220;

    const step = () => {
      if (ticksRef.current >= MAX) {
        if (!userInteractedRef.current) {
          fitToView();
        } else {
          renderCanvas();
        }
        return;
      }
      ticksRef.current++;
      const nl = Array.from(simMap.values());
      const n = nl.length;
      if (n === 0) return;

      const k = Math.sqrt((width * height) / Math.max(1, n)) * 1.4;

      // Efficient spatial-hash repulsion
      const cellSize = Math.max(80, k * 1.5);
      const grid = new Map<string, typeof nl>();
      nl.forEach(node => {
        const cx = Math.floor((node.x ?? 0) / cellSize);
        const cy = Math.floor((node.y ?? 0) / cellSize);
        const key = `${cx},${cy}`;
        if (!grid.has(key)) grid.set(key, []);
        grid.get(key)!.push(node);
      });

      nl.forEach(a => {
        const ax = a.x ?? 0, ay = a.y ?? 0;
        const cx = Math.floor(ax / cellSize);
        const cy = Math.floor(ay / cellSize);
        for (let dcx = -1; dcx <= 1; dcx++) {
          for (let dcy = -1; dcy <= 1; dcy++) {
            const neighbors = grid.get(`${cx + dcx},${cy + dcy}`);
            if (!neighbors) continue;
            for (const b of neighbors) {
              if (b === a) continue;
              const dx = ax - (b.x ?? 0), dy = ay - (b.y ?? 0);
              const dist2 = dx * dx + dy * dy || 1;
              const dist = Math.sqrt(dist2);
              if (dist > cellSize * 2.5) continue;
              const force = (k * k) / Math.max(30, dist) * 0.06;
              a.vx = (a.vx ?? 0) + (dx / dist) * force;
              a.vy = (a.vy ?? 0) + (dy / dist) * force;
            }
          }
        }
      });

      // Attraction along links
      filteredLinksRef.current.forEach(link => {
        const s = simMap.get(String(link.source)), t = simMap.get(String(link.target));
        if (!s || !t) return;
        const dx = (t.x ?? 0) - (s.x ?? 0), dy = (t.y ?? 0) - (s.y ?? 0);
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - k * 1.8) * 0.04;
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        s.vx = (s.vx ?? 0) + fx; s.vy = (s.vy ?? 0) + fy;
        t.vx = (t.vx ?? 0) - fx; t.vy = (t.vy ?? 0) - fy;
      });

      // Update positions + gravity toward center + damping + velocity clamping
      nl.forEach(n => {
        n.vx = ((n.vx ?? 0) + (width / 2 - (n.x ?? 0)) * 0.003) * 0.84;
        n.vy = ((n.vy ?? 0) + (height / 2 - (n.y ?? 0)) * 0.003) * 0.84;
        const maxV = 25;
        n.vx = Math.max(-maxV, Math.min(maxV, n.vx ?? 0));
        n.vy = Math.max(-maxV, Math.min(maxV, n.vy ?? 0));
        n.x = (n.x ?? 0) + (n.vx ?? 0);
        n.y = (n.y ?? 0) + (n.vy ?? 0);
      });

      if (ticksRef.current % 3 === 0 || ticksRef.current <= 5) renderCanvas();
      simLoopRef.current = requestAnimationFrame(step);
    };

    const initRaf = requestAnimationFrame(() => {
      resizeCanvas();
      renderCanvas();
      simLoopRef.current = requestAnimationFrame(step);
    });
    return () => { cancelAnimationFrame(initRaf); cancelAnimationFrame(simLoopRef.current); };
  }, [filteredNodes, filteredLinks, renderCanvas, resizeCanvas, fitToView]);

  // Non-passive wheel listener for smooth cursor-centered zoom
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      userInteractedRef.current = true;
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      const prevZoom = zoomLevelRef.current;
      const nz = Math.min(3, Math.max(0.25, prevZoom * zoomFactor));

      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const newPanX = mouseX - (mouseX - panOffsetRef.current.x) * (nz / prevZoom);
      const newPanY = mouseY - (mouseY - panOffsetRef.current.y) * (nz / prevZoom);

      panOffsetRef.current = { x: newPanX, y: newPanY };
      zoomLevelRef.current = nz;
      setZoomLevel(nz);
      renderCanvas();
    };
    canvas.addEventListener('wheel', onWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', onWheel);
  }, [renderCanvas]);

  // ResizeObserver — sizes canvas AND kicks off initial render after layout
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    resizeCanvas();
    const ro = new ResizeObserver(() => { resizeCanvas(); renderCanvas(); });
    ro.observe(container);
    const raf = requestAnimationFrame(() => { resizeCanvas(); renderCanvas(); });
    return () => { ro.disconnect(); cancelAnimationFrame(raf); };
  }, [resizeCanvas, renderCanvas]);

  // Fullscreen
  const toggleFullscreen = useCallback(() => {
    const el = wrapperRef.current;
    if (!el) return;
    if (!document.fullscreenElement) {
      el.requestFullscreen().then(() => setIsFullscreen(true)).catch(console.error);
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(console.error);
    }
  }, []);

  useEffect(() => {
    const onFsChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
      setTimeout(() => { resizeCanvas(); renderCanvas(); fitToView(); }, 120);
    };
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, [resizeCanvas, renderCanvas, fitToView]);

  // Hit-test helper
  const getNodeAtPoint = useCallback((cx: number, cy: number): GraphNodeData | null => {
    const wx = (cx - panOffsetRef.current.x) / zoomLevelRef.current;
    const wy = (cy - panOffsetRef.current.y) / zoomLevelRef.current;
    let found: GraphNodeData | null = null;
    simulationNodesRef.current.forEach(node => {
      const nx = node.x ?? 0, ny = node.y ?? 0;
      const r = node.type === "Project" ? 16 : 12;
      if (Math.sqrt((wx - nx) ** 2 + (wy - ny) ** 2) <= r + 6) found = node;
    });
    return found;
  }, []);

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (draggedNodeRef.current) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const node = getNodeAtPoint(e.clientX - rect.left, e.clientY - rect.top);
    setSelectedNode(node);
    selectedNodeRef.current = node;
    if (node && onNodeClick) onNodeClick(node);
    renderCanvas();
  }, [getNodeAtPoint, onNodeClick, renderCanvas]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    userInteractedRef.current = true;
    const rect = canvasRef.current!.getBoundingClientRect();
    const node = getNodeAtPoint(e.clientX - rect.left, e.clientY - rect.top);
    if (node) {
      draggedNodeRef.current = node;
      setSelectedNode(node); selectedNodeRef.current = node;
      if (onNodeClick) onNodeClick(node);
    } else {
      isDraggingRef.current = true;
      dragStartRef.current = { x: e.clientX - panOffsetRef.current.x, y: e.clientY - panOffsetRef.current.y };
    }
  }, [getNodeAtPoint, onNodeClick]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (draggedNodeRef.current) {
      const rect = canvasRef.current!.getBoundingClientRect();
      const wx = (e.clientX - rect.left - panOffsetRef.current.x) / zoomLevelRef.current;
      const wy = (e.clientY - rect.top - panOffsetRef.current.y) / zoomLevelRef.current;
      const n = simulationNodesRef.current.get(String(draggedNodeRef.current.id));
      if (n) { n.x = wx; n.y = wy; n.vx = 0; n.vy = 0; }
      ticksRef.current = 0;
      renderCanvas();
    } else if (isDraggingRef.current) {
      const np = { x: e.clientX - dragStartRef.current.x, y: e.clientY - dragStartRef.current.y };
      panOffsetRef.current = np;
      renderCanvas();
    }
  }, [renderCanvas]);

  const handleMouseUp = useCallback(() => {
    draggedNodeRef.current = null;
    isDraggingRef.current = false;
  }, []);

  const zoomIn = () => {
    userInteractedRef.current = true;
    const nz = Math.min(3, zoomLevelRef.current + 0.25);
    zoomLevelRef.current = nz;
    setZoomLevel(nz);
    renderCanvas();
  };

  const zoomOut = () => {
    userInteractedRef.current = true;
    const nz = Math.max(0.25, zoomLevelRef.current - 0.25);
    zoomLevelRef.current = nz;
    setZoomLevel(nz);
    renderCanvas();
  };

  const resetView = () => {
    userInteractedRef.current = false;
    fitToView();
  };

  const toggleTypeFilter = (type: string) => {
    setActiveTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type); else next.add(type);
      return next;
    });
  };

  const connectedLinks = useMemo(() => {
    if (!selectedNode) return [];
    return links.filter(l => String(l.source) === String(selectedNode.id) || String(l.target) === String(selectedNode.id));
  }, [selectedNode, links]);

  return (
    <div
      ref={wrapperRef}
      className={`flex flex-col lg:flex-row bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl ${isFullscreen ? "fixed inset-0 z-50 rounded-none border-0" : "h-[760px]"}`}
    >
      {/* Canvas Area */}
      <div
        ref={containerRef}
        className="relative flex-1 min-h-[420px] w-full bg-[#020617] overflow-hidden"
        style={{ cursor: isDraggingRef.current ? "grabbing" : "crosshair" }}
      >

        {/* Top Bar */}
        <div className="absolute top-3 left-3 right-3 z-20 flex flex-wrap items-center justify-between gap-2 bg-slate-900/95 backdrop-blur px-3 py-2 rounded-xl border border-slate-700/70 shadow-xl">
          <div className="relative flex-1 min-w-[150px] max-w-xs">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search nodes…"
              value={searchTerm}
              onChange={e => { setSearchTerm(e.target.value); searchTermRef.current = e.target.value; renderCanvas(); }}
              className="w-full bg-slate-950 text-slate-100 pl-8 pr-3 py-1.5 rounded-lg border border-slate-700 text-xs focus:outline-none focus:border-indigo-500 transition"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <button onClick={zoomIn} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition" title="Zoom In"><ZoomIn className="w-3.5 h-3.5" /></button>
            <button onClick={zoomOut} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition" title="Zoom Out"><ZoomOut className="w-3.5 h-3.5" /></button>
            <button onClick={resetView} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition" title="Reset View (Fit to Screen)">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 9V5H5v4h4zm0 10H5v-4h4v4zm10 0h-4v-4h4v4zm0-10h-4V5h4v4z" /></svg>
            </button>
            <button onClick={toggleFullscreen} className="p-1.5 bg-indigo-800 hover:bg-indigo-700 text-indigo-200 rounded-lg transition" title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}>
              {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
            {onRefresh && (
              <button onClick={onRefresh} className="flex items-center gap-1 px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition text-xs font-medium" title="Reload">
                <RefreshCw className="w-3 h-3" /> Reload
              </button>
            )}
          </div>
        </div>

        {/* Zoom % badge */}
        <div className="absolute top-[3.5rem] right-3 z-10 bg-slate-900/80 text-slate-400 text-[10px] font-mono px-2 py-0.5 rounded-lg border border-slate-700/50 select-none">
          {Math.round(zoomLevel * 100)}%
        </div>

        {/* Filter bar */}
        <div className="absolute bottom-3 left-3 right-3 z-20 flex flex-wrap items-center gap-1.5 bg-slate-900/95 backdrop-blur px-3 py-2 rounded-xl border border-slate-700/70 shadow-xl">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mr-1 flex items-center gap-1 flex-shrink-0">
            <Filter className="w-3 h-3" /> Types:
          </span>
          {ALL_NODE_TYPES.map(type => {
            const active = activeTypes.has(type);
            const s = TYPE_COLORS[type];
            return (
              <button key={type} onClick={() => toggleTypeFilter(type)}
                className={`text-[10px] font-medium px-2 py-0.5 rounded border transition flex items-center gap-1 ${active ? `${s.bg} ${s.text} ${s.border}` : "bg-slate-950/60 text-slate-600 border-slate-800 opacity-40 hover:opacity-75"}`}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: active ? s.colorHex : "#475569" }} />{type}
              </button>
            );
          })}
          <span className="ml-auto text-[10px] text-slate-500 font-mono flex-shrink-0">{filteredNodes.length}N · {filteredLinks.length}E</span>
        </div>

        {/* Canvas — wheel handled natively with passive:false via useEffect */}
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          style={{ display: "block", width: "100%", height: "100%" }}
        />

        {isLoading && (
          <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center z-30">
            <div className="flex flex-col items-center gap-3">
              <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
              <p className="text-sm font-medium text-slate-300">Constructing Knowledge Graph…</p>
            </div>
          </div>
        )}

        {!isLoading && filteredNodes.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-400 p-6 text-center pointer-events-none z-10">
            <Share2 className="w-10 h-10 text-slate-600 animate-pulse" />
            <p className="text-sm font-semibold text-slate-300">No Graph Nodes Available</p>
            <p className="text-xs text-slate-500 max-w-sm">
              No extracted entities or relationships match the selected filters. Click "Reload" or "Reconstruct" to refresh the graph.
            </p>
          </div>
        )}
      </div>

      {/* Inspector Panel */}
      <div className={`${isFullscreen ? "w-72" : "w-full lg:w-72"} bg-slate-900 border-t lg:border-t-0 lg:border-l border-slate-800 p-4 flex flex-col gap-4 overflow-y-auto flex-shrink-0`}>
        <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
          <Share2 className="w-4 h-4" /> Node Inspector
        </div>

        {selectedNode ? (
          <div className="space-y-3">
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
              <span className={`inline-block text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border mb-2 ${TYPE_COLORS[selectedNode.type]?.bg} ${TYPE_COLORS[selectedNode.type]?.text} ${TYPE_COLORS[selectedNode.type]?.border}`}>
                {selectedNode.type}
              </span>
              <h4 className="text-sm font-bold text-slate-100 leading-snug">{selectedNode.name}</h4>
              <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
                <Tag className="w-3 h-3 text-slate-500" /> ID: <span className="font-mono text-slate-300">{selectedNode.id}</span>
              </p>
              <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-slate-400">Degree Connections:</span>
                <span className="font-bold text-indigo-300 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-800">
                  {selectedNode.degree || connectedLinks.length} edges
                </span>
              </div>
            </div>
            <div>
              <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Connected Neighborhood ({connectedLinks.length})
              </h5>
              <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
                {connectedLinks.length > 0 ? connectedLinks.map((link, idx) => {
                  const otherId = link.source === selectedNode.id ? link.target : link.source;
                  const otherNode = nodes.find(n => n.id === otherId);
                  return (
                    <div key={idx}
                      className="bg-slate-950/60 px-2.5 py-2 rounded-lg border border-slate-800 text-xs flex items-center justify-between gap-2 cursor-pointer hover:border-slate-700 transition"
                      onClick={() => { if (otherNode) { setSelectedNode(otherNode); selectedNodeRef.current = otherNode; renderCanvas(); } }}>
                      <div className="min-w-0">
                        <span className="text-[9px] text-slate-500 block font-mono uppercase tracking-wide">{link.relationship}</span>
                        <span className="font-medium text-slate-200 truncate block">{otherNode?.name || String(otherId)}</span>
                      </div>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded border flex-shrink-0 ${TYPE_COLORS[otherNode?.type || ""]?.bg || "bg-slate-800"} ${TYPE_COLORS[otherNode?.type || ""]?.text || "text-slate-300"} ${TYPE_COLORS[otherNode?.type || ""]?.border || "border-slate-600"}`}>
                        {otherNode?.type || "Node"}
                      </span>
                    </div>
                  );
                }) : <p className="text-xs text-slate-500 italic">No connected links in current view.</p>}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-slate-950/60 p-5 rounded-xl border border-slate-800 text-center text-xs space-y-2">
            <Info className="w-7 h-7 text-slate-600 mx-auto" />
            <p className="font-medium text-slate-300">Click any node to inspect connections.</p>
            <div className="text-[11px] text-slate-500 space-y-1 text-left pt-1">
              <p><b>Click node</b> — inspect it</p>
              <p><b>Drag node</b> — reposition</p>
              <p><b>Drag canvas</b> — pan view</p>
              <p><b>Scroll</b> — zoom in/out</p>
              <p><b>Fullscreen</b> button — expand</p>
              {highlightNames && highlightNames.size > 0 && (
                <p className="text-amber-400 font-medium"><b>Golden glow</b> = shared entity</p>
              )}
            </div>
          </div>
        )}

        <div className="pt-3 border-t border-slate-800 mt-auto">
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Legend</p>
          <div className="grid grid-cols-2 gap-1">
            {ALL_NODE_TYPES.map(type => (
              <div key={type} className="flex items-center gap-1.5 text-[10px] text-slate-400">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: TYPE_COLORS[type].colorHex }} />{type}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
