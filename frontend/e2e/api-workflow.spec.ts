import { test, expect, type APIRequestContext } from "@playwright/test";
const base = "http://127.0.0.1:8000/api/v1";
async function create(request: APIRequestContext) {
  const r = await request.post(`${base}/sessions`, {
    data: { name: "HTTP contract verification" },
  });
  expect(r.status()).toBe(201);
  const { data } = await r.json();
  return `${base}/sessions/${data.id}`;
}
async function data(request: APIRequestContext, path: string, body?: unknown) {
  const r =
    body === undefined
      ? await request.get(path)
      : await request.post(path, { data: body });
  expect(r.ok(), await r.text()).toBeTruthy();
  return (await r.json()).data;
}
test("real API sample contracts: editor, offline suggestions, versioning, build reports, graph and binary snapshots", async ({
  request,
}) => {
  const p = await create(request);
  try {
    expect(
      (
        await request.put(`${p}/scope`, {
          data: {
            project: "Retail",
            business_questions: ["Which customers place orders?"],
          },
        })
      ).ok(),
    ).toBeTruthy();
    await data(request, `${p}/sources/sample`, {});
    await data(request, `${p}/metadata/extract`, {});
    await data(request, `${p}/metadata/analyze`, {});
    for (const route of [
      "/sources",
      "/metadata",
      "/metadata/tables",
      "/metadata/analysis",
      "/metadata/columns?table=public.customers",
      "/metadata/preview?table=public.customers&limit=2",
    ])
      await data(request, p + route);
    const initialized = await data(request, `${p}/ontology/draft`, {
      mode: "template",
    });
    const ontology = initialized.ontology;
    expect(
      (await request.put(`${p}/ontology/draft`, { data: { ontology } })).ok(),
    ).toBeTruthy();
    const original = ontology.classes[0];
    const definition = { ...original, name: "ContractEntity" };
    await data(request, `${p}/ontology/classes`, { definition });
    expect(
      (
        await request.patch(`${p}/ontology/classes/ContractEntity`, {
          data: { name: "ContractRenamed" },
        })
      ).ok(),
    ).toBeTruthy();
    expect(
      (
        await request.put(`${p}/ontology/classes/ContractRenamed/attributes`, {
          data: { attributes: original.attributes },
        })
      ).ok(),
    ).toBeTruthy();
    expect(
      (await request.delete(`${p}/ontology/classes/ContractRenamed`)).ok(),
    ).toBeTruthy();
    const rel = { ...ontology.relationships[0], name: "CONTRACT_LINK" };
    await data(request, `${p}/ontology/relationships`, { definition: rel });
    expect(
      (
        await request.delete(`${p}/ontology/relationships`, {
          params: {
            key: `${rel.source_class}-[${rel.name}]->${rel.target_class}`,
          },
        })
      ).ok(),
    ).toBeTruthy();
    await data(request, `${p}/ontology/draft/save`, {});
    await data(request, `${p}/ontology/draft/revert`, {});
    await data(request, `${p}/ontology/draft/save`, {});
    const suggestions = await data(request, `${p}/ontology/suggestions`, {
      actor: "data.modeller",
      use_groq: false,
      include_samples: false,
    });
    expect(suggestions.length).toBeGreaterThan(0);
    await data(request, `${p}/ontology/suggestions`);
    const decisions = Object.fromEntries(
      suggestions
        .filter((i: { kind: string }) => i.kind !== "duplicate")
        .map((i: { item_id: string; status: string }) => [
          i.item_id,
          { action: i.status === "invalid" ? "reject" : "approve" },
        ]),
    );
    const review = {
      actor: "data.modeller",
      decisions,
      acyclic_relationships: ["Customer-[REFERRED]->Customer"],
    };
    await data(request, `${p}/ontology/review/preview`, review);
    await data(request, `${p}/ontology/review`, review);
    expect((await data(request, `${p}/ontology/validate`, {})).ok).toBe(true);
    await data(request, `${p}/ontology/validation`);
    await data(request, `${p}/ontology/approve`, {
      author: "data.modeller",
      reviewer: "reviewer.lead",
    });
    await data(request, `${p}/ontology/versions?ontology_id=retail`);
    await data(request, `${p}/ontology/versions/1?ontology_id=retail`);
    await data(request, `${p}/ontology/audit?ontology_id=retail`);
    for (let stage = 10; stage <= 15; stage++) {
      await data(request, `${p}/builds/stages/${stage}`, {});
      await data(request, `${p}/builds/stages/${stage}`);
    }
    await data(
      request,
      `${p}/builds/extracted-rows?table=public.customers&limit=2`,
    );
    for (const kind of ["merges", "changes", "quarantine", "records"])
      await data(request, `${p}/builds/cleaning/${kind}?limit=2`);
    const graph = await data(
      request,
      `${p}/graphs/data?limit=50&edge_limit=100&labels=Customer&labels=Order`,
    );
    expect(graph.nodes.length).toBeGreaterThan(0);
    const node = graph.edges[0].source;
    const pathTarget=graph.edges[0].target;
    await data(request, `${p}/graphs/nodes?offset=0&limit=2`);
    await data(request, `${p}/graphs/node?node_id=${encodeURIComponent(node)}`);
    expect(
      (
        await data(
          request,
          `${p}/graphs/path?source=${encodeURIComponent(node)}&target=${encodeURIComponent(pathTarget)}&max_hops=1`,
        )
      ).connected,
    ).toBe(true);
    await data(request, `${p}/graphs/metrics`);
    const snapshot = await data(request, `${p}/graphs/snapshots`, {});
    expect(snapshot.reload_check).toBe(true);
    await data(
      request,
      `${p}/graphs/snapshots?ontology_id=${snapshot.ontology_id}`,
    );
    await data(
      request,
      `${p}/graphs/snapshots/${snapshot.build_id}/current?ontology_id=${snapshot.ontology_id}`,
      {},
    );
    for (const artifact of [
      "graph.json.gz",
      "graph.graphml",
      "quarantine.json",
      "manifest.json",
    ]) {
      const r = await request.get(
        `${p}/graphs/snapshots/${snapshot.build_id}/download/${artifact}?ontology_id=${snapshot.ontology_id}`,
      );
      expect(r.ok()).toBeTruthy();
      expect((await r.body()).length).toBeGreaterThan(0);
      expect(r.headers()["content-disposition"]).toContain(artifact);
    }
    await data(
      request,
      `${p}/graphs/data?ontology_id=retail&build_id=${snapshot.build_id}`,
    );
    await data(request, `${p}/events?offset=0&limit=5`);
    await data(
      request,
      `${p}/ontology/versions/1/rollback?ontology_id=retail`,
      { actor: "rollback.modeller" },
    );
    await data(request, `${p}/ontology/use-approved?ontology_id=retail`, {});
    await data(request, `${p}/builds`, { batch_size: 2 });
    await expect
      .poll(
        async () => {
          const job = await data(request, `${p}/builds/status`);
          return job.status;
        },
        { timeout: 30000 },
      )
      .toBe("completed");
  } finally {
    expect((await request.delete(p)).status()).toBe(204);
  }
});
test("real API CSV workflow rejects invalid files, preserves previous source, and builds schema-drafted data", async ({
  request,
}) => {
  const p = await create(request);
  try {
    await request.put(`${p}/scope`, {
      data: {
        project: "Customer 360",
        business_questions: ["How are accounts linked?"],
      },
    });
    const fs = await import("node:fs");
    const path = await import("node:path");
    const form = new FormData();
    for (const filename of fs.readdirSync("../data/samples/customer360"))
      if (filename.endsWith(".csv"))
        form.append(
          "files",
          new File(
            [
              fs.readFileSync(
                path.join("../data/samples/customer360", filename),
              ),
            ],
            filename,
          ),
        );
    const uploaded = await request.post(`${p}/sources/upload`, {
      multipart: form,
    });
    expect(uploaded.ok(), await uploaded.text()).toBeTruthy();
    const before = await data(request, `${p}/sources`);
    const rejected = await request.post(`${p}/sources/upload`, {
      multipart: {
        files: {
          name: "bad.xlsx",
          mimeType: "application/octet-stream",
          buffer: Buffer.from("bad"),
        },
      },
    });
    expect(rejected.status()).toBe(422);
    expect(await data(request, `${p}/sources`)).toEqual(before);
    await data(request, `${p}/metadata/extract`, {});
    await data(request, `${p}/metadata/analyze`, {});
    await data(request, `${p}/ontology/draft`, {
      mode: "schema",
      ontology_id: "customer360",
      name: "Customer 360",
    });
    await data(request, `${p}/ontology/draft/save`, {});
    await data(request, `${p}/ontology/suggestions/skip`, {});
    await data(request, `${p}/ontology/review`, { actor: "data.modeller" });
    expect((await data(request, `${p}/ontology/validate`, {})).ok).toBe(true);
    await data(request, `${p}/ontology/approve`, {
      author: "data.modeller",
      reviewer: "reviewer.lead",
    });
    await data(request, `${p}/builds`, {});
    await expect
      .poll(async () => (await data(request, `${p}/builds/status`)).status, {
        timeout: 30000,
      })
      .toBe("completed");
    const metrics = await data(request, `${p}/graphs/metrics`);
    expect(metrics.nodes).toBe(54);
    expect(metrics.edges).toBe(64);
  } finally {
    await request.delete(p);
  }
});
