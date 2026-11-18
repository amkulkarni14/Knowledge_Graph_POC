import { useEffect } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  type Node,
  type Edge,
} from "@xyflow/react";
export function OntologyCanvas({
  nodes: initialNodes,
  edges,
  onSelect,
}: {
  nodes: Node[];
  edges: Edge[];
  onSelect: (name: string) => void;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  useEffect(
    () =>
      setNodes((previous) =>
        initialNodes.map((node) => ({
          ...node,
          position:
            previous.find((n) => n.id === node.id)?.position ?? node.position,
        })),
      ),
    [initialNodes, setNodes],
  );
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      fitView
      nodesDraggable
      nodesConnectable={false}
      onNodeClick={(_, node) => onSelect(node.id)}
    >
      <Background />
      <Controls />
    </ReactFlow>
  );
}
