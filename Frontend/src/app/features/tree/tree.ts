import {
  Component, inject, signal, OnInit, OnDestroy,
  ElementRef, ViewChild, ChangeDetectorRef
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import * as d3 from 'd3';
import { AppShellComponent } from '../../shared/components/app-shell/app-shell';
import { PersonService } from '../../services/person.service';
import { Person } from '../../models/person.model';
import { environment } from '../../../environments/environment';

const API = environment.apiUrl;

// ── Card geometry ─────────────────────────────────────────────────────────────
const CW = 160;   // card width
const CH = 78;    // card height
const HG = 50;    // horizontal gap between cards
const VG = 80;    // vertical gap between generations
const MARGIN = 40;

// ── Data interfaces ───────────────────────────────────────────────────────────
interface PersonNode {
  id: string;
  first_name: string;
  last_name: string;
  birth_date?: string | null;
  gender?: string | null;
  is_living?: boolean;
  class?: string;
  generation?: number;
}

interface FlatEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  class?: string;
}

interface TreeData {
  nodes: { data: PersonNode }[];
  edges: { data: FlatEdge }[];
}

type ViewType = 'family' | 'ancestors' | 'descendants';

// ── Component ─────────────────────────────────────────────────────────────────
@Component({
  selector: 'app-tree',
  standalone: true,
  imports: [AppShellComponent, FormsModule],
  templateUrl: './tree.html',
  styleUrl: './tree.css',
})
export class TreeComponent implements OnInit, OnDestroy {
  @ViewChild('treeWrap') treeWrap!: ElementRef<HTMLDivElement>;

  private http = inject(HttpClient);
  private pSvc = inject(PersonService);
  private cdr  = inject(ChangeDetectorRef);

  persons    = signal<Person[]>([]);
  selectedId = signal('');
  viewType   = signal<ViewType>('family');
  loading    = signal(false);
  error      = signal<string | null>(null);
  hasData    = signal(false);

  ngOnInit() {
    this.pSvc.list(1, 200).subscribe({ next: r => this.persons.set(r.items) });
  }

  visualize() {
    const id = this.selectedId();
    if (!id) return;
    this.loading.set(true);
    this.error.set(null);
    this.hasData.set(false);

    const vt = this.viewType();
    const urlMap: Record<ViewType, string> = {
      family:      `${API}/tree/family/${id}`,
      ancestors:   `${API}/tree/ancestors/${id}?generations=4`,
      descendants: `${API}/tree/descendants/${id}?generations=3`,
    };

    this.http.get<TreeData>(urlMap[vt]).subscribe({
      next: data => {
        this.loading.set(false);
        if (!data.nodes.length) {
          this.error.set('Aucune relation trouvée. Ajoutez des filiations ou unions depuis la fiche du membre.');
          return;
        }
        this.hasData.set(true);
        this.cdr.detectChanges();
        setTimeout(() => this.render(data, vt, id), 0);
      },
      error: () => {
        this.loading.set(false);
        this.error.set("Impossible de charger l'arbre généalogique.");
      }
    });
  }

  // ── Render dispatcher ───────────────────────────────────────────────────────
  private render(data: TreeData, vt: ViewType, rootId: string) {
    const el = this.treeWrap?.nativeElement;
    if (!el) return;
    d3.select(el).selectAll('*').remove();

    const nodes   = data.nodes.map(n => n.data);
    const edges   = data.edges.map(e => e.data);
    const nodeMap = new Map<string, PersonNode>(nodes.map(n => [n.id, n]));
    const W       = el.clientWidth || 900;

    const { positions, drawEdges, totalW, totalH } =
      vt === 'family'
        ? this.layoutFamily(nodes, edges, rootId, W)
        : this.layoutHierarchy(nodes, edges, nodeMap, rootId, vt === 'ancestors');

    this.drawSvg(el, Math.max(W, totalW), totalH, positions, nodeMap, drawEdges);
  }

  // ── Layout: family (3-row custom) ───────────────────────────────────────────
  private layoutFamily(
    nodes: PersonNode[], edges: FlatEdge[], rootId: string, W: number
  ) {
    const pos     = new Map<string, { x: number; y: number }>();
    const ROW     = CH + VG;

    const center  = nodes.find(n => n.class === 'center' || n.id === rootId)!;
    const parents = nodes.filter(n => n.class === 'parent');
    const spouses = nodes.filter(n => n.class === 'spouse');
    const children = nodes.filter(n => n.class === 'child');

    const place = (list: PersonNode[], row: number) => {
      const total = list.length * CW + (list.length - 1) * HG;
      const startX = Math.max(MARGIN, (W - total) / 2);
      list.forEach((p, i) => pos.set(p.id, { x: startX + i * (CW + HG), y: row * ROW + MARGIN }));
    };

    let row = 0;
    if (parents.length)  { place(parents, row++); }
    const coupleRow = row++;
    const couple = center ? [center, ...spouses] : spouses;
    place(couple, coupleRow);
    if (children.length) { place(children, row++); }

    const maxX = [...pos.values()].reduce((m, p) => Math.max(m, p.x + CW), 0);
    const maxY = [...pos.values()].reduce((m, p) => Math.max(m, p.y + CH), 0);

    return { positions: pos, drawEdges: edges, totalW: maxX + MARGIN, totalH: maxY + MARGIN };
  }

  // ── Layout: D3 tree hierarchy (ancestors / descendants) ─────────────────────
  private layoutHierarchy(
    nodes: PersonNode[], edges: FlatEdge[],
    nodeMap: Map<string, PersonNode>, rootId: string, isAncestors: boolean
  ) {
    // Build adjacency: for ancestors, treat parents as d3-children (reversed)
    const adj = new Map<string, string[]>(nodes.map(n => [n.id, []]));
    for (const e of edges) {
      const [parent, child] = isAncestors ? [e.target, e.source] : [e.source, e.target];
      if (!adj.has(parent)) adj.set(parent, []);
      adj.get(parent)!.push(child);
    }

    interface HNode { id: string; children?: HNode[] }
    const visited = new Set<string>();
    const buildNode = (id: string): HNode => {
      visited.add(id);
      const kids = (adj.get(id) ?? []).filter(c => !visited.has(c)).map(c => buildNode(c));
      return kids.length ? { id, children: kids } : { id };
    };

    const rootData = buildNode(rootId);
    const root = d3.hierarchy(rootData, d => (d as any).children);

    const treeLayout = d3.tree<{ id: string }>().nodeSize([CW + HG, CH + VG]);
    treeLayout(root as d3.HierarchyNode<{ id: string }>);

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    const rawPos = new Map<string, { x: number; y: number }>();

    (root.descendants() as any[]).forEach(d => {
      const y = isAncestors ? -d.y : d.y;
      rawPos.set(d.data.id, { x: d.x, y });
      minX = Math.min(minX, d.x);
      maxX = Math.max(maxX, d.x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    });

    const pos = new Map<string, { x: number; y: number }>();
    rawPos.forEach((p, id) => pos.set(id, {
      x: p.x - minX + MARGIN,
      y: p.y - minY + MARGIN,
    }));

    // For ancestors, the logical edge direction is reversed for drawing
    const drawEdges: FlatEdge[] = isAncestors
      ? edges.map(e => ({ ...e, source: e.target, target: e.source }))
      : edges;

    const totalW = maxX - minX + CW + MARGIN * 2;
    const totalH = maxY - minY + CH + MARGIN * 2;
    return { positions: pos, drawEdges, totalW, totalH };
  }

  // ── SVG drawing ──────────────────────────────────────────────────────────────
  private drawSvg(
    el: HTMLElement,
    W: number, H: number,
    positions: Map<string, { x: number; y: number }>,
    nodeMap: Map<string, PersonNode>,
    edges: FlatEdge[]
  ) {
    const svg = d3.select(el).append('svg')
      .attr('width', '100%').attr('height', Math.max(500, H + 20))
      .attr('viewBox', `0 0 ${W} ${Math.max(500, H + 20)}`);

    // Drop shadow filter
    const defs = svg.append('defs');
    const f = defs.append('filter').attr('id', 'cshadow')
      .attr('x', '-10%').attr('y', '-10%').attr('width', '120%').attr('height', '130%');
    f.append('feDropShadow')
      .attr('dx', 0).attr('dy', 2).attr('stdDeviation', 4)
      .attr('flood-color', 'rgba(0,0,0,0.09)');

    const g = svg.append('g');

    // Zoom + pan
    svg.call(
      (d3.zoom<SVGSVGElement, unknown>())
        .scaleExtent([0.15, 3])
        .on('zoom', ev =>
          g.attr('transform', (ev as d3.D3ZoomEvent<SVGSVGElement, unknown>).transform.toString())
        )
    );

    // ── Edges ──────────────────────────────────────────────────────────────────
    const edgeG = g.append('g');
    for (const e of edges) {
      const sp = positions.get(e.source);
      const tp = positions.get(e.target);
      if (!sp || !tp) continue;

      const isCouple = e.class === 'couple' || e.label === 'spouse';

      if (isCouple) {
        // Horizontal dashed line at card mid-height between spouses
        const sy = sp.y + CH / 2;
        const ty = tp.y + CH / 2;
        const avgY = (sy + ty) / 2;
        edgeG.append('line')
          .attr('x1', sp.x + CW).attr('y1', avgY)
          .attr('x2', tp.x).attr('y2', avgY)
          .attr('stroke', '#f59e0b').attr('stroke-width', 2)
          .attr('stroke-dasharray', '6,3');
      } else {
        // Elbow connector: bottom of parent → top of child
        const sx = sp.x + CW / 2;
        const sy = sp.y + CH;
        const tx = tp.x + CW / 2;
        const ty = tp.y;
        const my = (sy + ty) / 2;
        edgeG.append('path')
          .attr('d', `M${sx},${sy} L${sx},${my} L${tx},${my} L${tx},${ty}`)
          .attr('fill', 'none')
          .attr('stroke', '#94a3b8').attr('stroke-width', 1.8)
          .attr('stroke-linecap', 'round');
      }
    }

    // ── Nodes (cards) ──────────────────────────────────────────────────────────
    for (const [id, pos] of positions) {
      const node = nodeMap.get(id);
      if (!node) continue;

      const isMale   = node.gender === 'male';
      const isFemale = node.gender === 'female';
      const isDead   = !node.is_living;

      // Theme colors
      const bgFill     = isDead ? '#f3f4f6' : isMale ? '#eff6ff' : isFemale ? '#fdf2f8' : '#f0fdf9';
      const borderCol  = isDead ? '#d1d5db' : isMale ? '#93c5fd' : isFemale ? '#f9a8d4' : '#6ee7b7';
      const avatarFill = isDead ? '#9ca3af' : isMale ? '#3b82f6' : isFemale ? '#ec4899' : '#10b981';
      const avatarText = '#fff';

      const card = g.append('g')
        .attr('transform', `translate(${pos.x},${pos.y})`)
        .attr('cursor', 'default');

      // Background rect
      card.append('rect')
        .attr('width', CW).attr('height', CH)
        .attr('rx', 12).attr('ry', 12)
        .attr('fill', bgFill)
        .attr('stroke', borderCol).attr('stroke-width', 1.5)
        .attr('filter', 'url(#cshadow)');

      // Avatar circle
      const AX = 33, AY = CH / 2;
      card.append('circle')
        .attr('cx', AX).attr('cy', AY).attr('r', 20)
        .attr('fill', avatarFill);

      // Initials
      const initials = `${node.first_name?.[0] ?? ''}${node.last_name?.[0] ?? ''}`.toUpperCase();
      card.append('text')
        .attr('x', AX).attr('y', AY)
        .attr('text-anchor', 'middle').attr('dominant-baseline', 'central')
        .attr('fill', avatarText).attr('font-size', '12').attr('font-weight', '700')
        .attr('font-family', 'inherit')
        .text(initials);

      // Text area starts after avatar
      const TX = AX + 20 + 10;
      const trunc = (s: string, n: number) => s.length > n ? s.slice(0, n - 1) + '…' : s;
      const availW = CW - TX - 8;
      const charsPerPx = 7;
      const maxChars = Math.floor(availW / charsPerPx);

      // First name
      card.append('text')
        .attr('x', TX).attr('y', AY - 13)
        .attr('font-size', '11.5').attr('font-weight', '600').attr('fill', '#1e293b')
        .attr('font-family', 'inherit')
        .text(trunc(node.first_name ?? '', maxChars));

      // Last name (uppercase)
      card.append('text')
        .attr('x', TX).attr('y', AY + 1)
        .attr('font-size', '10.5').attr('font-weight', '700').attr('fill', '#374151')
        .attr('font-family', 'inherit')
        .text(trunc((node.last_name ?? '').toUpperCase(), maxChars));

      // Birth year
      const year = this.extractYear(node.birth_date);
      card.append('text')
        .attr('x', TX).attr('y', AY + 15)
        .attr('font-size', '10').attr('fill', '#6b7280')
        .attr('font-family', 'inherit')
        .text(year ? `Né(e) en ${year}` : (node.is_living === false ? 'Décédé(e)' : ''));

      // Tooltip
      card.append('title')
        .text(`${node.first_name} ${node.last_name}` + (year ? ` · ${year}` : ''));
    }
  }

  private extractYear(d: string | null | undefined): number | null {
    if (!d) return null;
    const m = String(d).match(/\d{4}/);
    return m ? +m[0] : null;
  }

  ngOnDestroy() {}
}
