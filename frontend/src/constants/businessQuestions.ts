export interface BusinessQuestion {
  id: string;
  text: string;
  category?: string;
  source: "predefined" | "custom";
}

type SuggestedQuestion = BusinessQuestion & {
  category: string;
  source: "predefined";
};

const catalog: ReadonlyArray<{
  category: string;
  questions: ReadonlyArray<readonly [string, string]>;
}> = [
  {
    category: "Entity Discovery",
    questions: [
      ["key-entities", "What are the key entities in the dataset?"],
      ["entity-attributes", "What attributes are associated with each entity?"],
      ["entity-count", "How many unique entities exist?"],
      ["common-attributes", "Which entities share common attributes?"],
      ["incomplete-entities", "Which entities have incomplete information?"],
    ],
  },
  {
    category: "Relationship Discovery",
    questions: [
      ["entity-connections", "How are different entities connected?"],
      ["entity-relationships", "What relationships exist between entities?"],
      [
        "highest-connections",
        "Which entities have the highest number of connections?",
      ],
      ["isolated-entities", "Are there any isolated entities?"],
      ["relationship-types", "What are the most common relationship types?"],
    ],
  },
  {
    category: "Dependency and Impact Analysis",
    questions: [
      ["dependents", "What entities depend on a particular entity?"],
      [
        "downstream-impact",
        "What downstream entities are impacted by a change?",
      ],
      [
        "upstream-contributors",
        "What upstream entities contribute to a particular outcome?",
      ],
      ["dependency-chains", "What are the critical dependency chains?"],
      ["points-of-failure", "Are there any single points of failure?"],
    ],
  },
  {
    category: "Data Quality and Consistency",
    questions: [
      ["duplicates", "Are there duplicate entities in the dataset?"],
      ["missing-information", "Which records contain missing information?"],
      [
        "conflicting-attributes",
        "Are there conflicting attributes across data sources?",
      ],
      ["validation", "Which entities require data validation?"],
      [
        "data-quality",
        "What data quality issues exist across connected records?",
      ],
    ],
  },
  {
    category: "Graph Analytics",
    questions: [
      [
        "influential-entities",
        "Which entities are most influential in the network?",
      ],
      ["communities", "What communities or clusters exist?"],
      ["shortest-path", "What is the shortest path between two entities?"],
      ["bridges", "Which entities act as bridges between different groups?"],
      ["unusual-relationships", "Are there unusual relationship patterns?"],
    ],
  },
  {
    category: "Traceability and Lineage",
    questions: [
      ["entity-origin", "Where did a particular entity or record originate?"],
      ["entity-history", "How has an entity changed over time?"],
      ["source-records", "Which source records contributed to an entity?"],
      [
        "relationship-path",
        "What is the complete relationship path between two entities?",
      ],
      [
        "system-trace",
        "Can we trace information across multiple connected systems?",
      ],
    ],
  },
  {
    category: "Risk and Anomaly Detection",
    questions: [
      ["unusual-behavior", "Which entities exhibit unusual behavior?"],
      [
        "relationship-risks",
        "What potential risks can be identified from relationships?",
      ],
      [
        "issue-impact",
        "Which connected entities may be affected by a detected issue?",
      ],
      [
        "relationship-changes",
        "Are there unexpected changes in relationship patterns?",
      ],
      ["investigation", "Which entities require further investigation?"],
    ],
  },
];

export const suggestedQuestions: SuggestedQuestion[] = catalog.flatMap(
  ({ category, questions }) =>
    questions.map(([id, text]) => ({
      id,
      text,
      category,
      source: "predefined",
    })),
);

export const questionLimit = 100;
export const questionLength = 200;
export const questionKey = (text: string) =>
  text.normalize("NFKC").trim().replace(/\s+/g, " ").toLowerCase();

const knownByText = new Map(
  suggestedQuestions.map((question) => [question.text, question]),
);

export function restoreBusinessQuestions(texts: string[]): BusinessQuestion[] {
  const seen = new Set<string>();
  return texts.map((text, index) => {
    const known = knownByText.get(text);
    const first = !seen.has(text);
    seen.add(text);
    if (known && first) return known;
    return {
      ...known,
      id: `saved:${index}`,
      text,
      source: known?.source ?? "custom",
    };
  });
}
