
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { MemoryNode, MemoryEdge } from '../types';
import { getGraphData } from '../services/geminiService';

const MemoryGraph: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [graphData, setGraphData] = useState<{ nodes: MemoryNode[], edges: MemoryEdge[] }>({ nodes: [], edges: [] });

  useEffect(() => {
    const fetchData = async () => {
      const data = await getGraphData();
      // Transform backend nodes to frontend MemoryNodes if needed
      const nodes = data.nodes.map((n: any) => ({
        id: n.id,
        label: n.label,
        type: n.constraints.length > 0 ? 'Intent' : 'Code', // Simple heuristic
        status: n.status
      }));
      const edges = data.edges || [];
      setGraphData({ nodes, edges });
    };
    fetchData();
  }, []);

  useEffect(() => {
    if (!svgRef.current || graphData.nodes.length === 0) return;

    // Use fresh clones to prevent D3 from mutating state directly
    const nodes = JSON.parse(JSON.stringify(graphData.nodes));
    const links = JSON.parse(JSON.stringify(graphData.edges));

    const width = svgRef.current.clientWidth || 800;
    const height = svgRef.current.clientHeight || 600;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // High-Fidelity Filters
    const defs = svg.append("defs");

    const glow = defs.append("filter")
      .attr("id", "high-glow")
      .attr("x", "-100%")
      .attr("y", "-100%")
      .attr("width", "300%")
      .attr("height", "300%");

    glow.append("feGaussianBlur")
      .attr("stdDeviation", "4")
      .attr("result", "blur");

    glow.append("feComposite")
      .attr("in", "SourceGraphic")
      .attr("in2", "blur")
      .attr("operator", "over");

    const simulation = d3.forceSimulation(nodes as any)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(180))
      .force("charge", d3.forceManyBody().strength(-800))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(60));

    const link = svg.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "rgba(14, 165, 233, 0.1)")
      .attr("stroke-width", 1.5)
      .attr("stroke-dasharray", "4 4");

    const pulseGroup = svg.append("g");

    const node = svg.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(d3.drag<any, any>()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }));

    node.append("circle")
      .attr("r", 12)
      .attr("fill", (d: any) => {
        switch (d.type) {
          case 'Code': return '#10b981';
          case 'Intent': return '#0ea5e9';
          case 'Fact': return '#f59e0b';
          default: return '#6366f1';
        }
      })
      .attr("filter", "url(#high-glow)")
      .attr("opacity", 0.8)
      .attr("class", "cursor-pointer");

    node.append("text")
      .text((d: any) => d.label)
      .attr("dx", 24)
      .attr("dy", 4)
      .attr("fill", "rgba(255, 255, 255, 0.6)")
      .attr("font-size", "11px")
      .attr("font-family", "JetBrains Mono")
      .attr("font-weight", "bold")
      .style("pointer-events", "none")
      .attr("letter-spacing", "0.1em");

    let frame = 0;
    simulation.on("tick", () => {
      frame++;

      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);

      // Kinematic Data Pulses
      if (frame % 45 === 0) {
        links.forEach((l: any) => {
          if (Math.random() > 0.6) {
            pulseGroup.append("circle")
              .attr("r", 2)
              .attr("fill", "#0ea5e9")
              .attr("filter", "url(#high-glow)")
              .attr("cx", l.source.x)
              .attr("cy", l.source.y)
              .transition()
              .duration(2500)
              .ease(d3.easeCubicOut)
              .attr("cx", l.target.x)
              .attr("cy", l.target.y)
              .attr("opacity", 0)
              .remove();
          }
        });
      }
    });

    return () => simulation.stop();
  }, []);

  return (
    <div className="w-full h-full relative glass rounded-[3rem] overflow-hidden border border-white/5 shadow-2xl">
      <div className="absolute top-12 left-12 z-10 space-y-6 pointer-events-none">
        <div className="flex items-center gap-5">
          <div className="w-3 h-3 rounded-full bg-sky-500 animate-ping shadow-[0_0_15px_#0ea5e9]" />
          <h3 className="text-lg font-bold text-white tracking-[0.5em] uppercase mono">Neural Semantic Topology</h3>
        </div>
        <div className="p-6 bg-black/40 border-l-2 border-sky-500/30 backdrop-blur-xl space-y-3">
          <p className="text-[11px] text-slate-500 max-w-sm leading-relaxed mono">
            Real-time relational extraction active. Monitoring cross-node logic dependencies. Data flow pulses indicate active semantic inference cycles.
          </p>
        </div>
      </div>

      <div className="absolute bottom-12 right-12 z-10 flex gap-10 px-10 py-5 glass rounded-3xl border border-white/10 shadow-2xl">
        <LegendItem color="bg-emerald-500" label="Implementation" />
        <LegendItem color="bg-sky-500" label="Intent" />
        <LegendItem color="bg-amber-500" label="Oracle" />
        <LegendItem color="bg-indigo-500" label="Deps" />
      </div>

      <svg ref={svgRef} className="w-full h-full cursor-crosshair" />
    </div>
  );
};

const LegendItem = ({ color, label }: any) => (
  <div className="flex items-center space-x-3">
    <div className={`w-2 h-2 rounded-full ${color} bloom`} />
    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mono">{label}</span>
  </div>
);

export default MemoryGraph;
