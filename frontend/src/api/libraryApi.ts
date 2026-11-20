import { useQuery } from "@tanstack/react-query";
import { get, send } from "./client";
import type { Schema } from "../types/common.types";

export const libraryApi = {
  domains: (signal?: AbortSignal) =>
    get<Schema<"SavedDomain">[]>("/domains", undefined, signal),
  createDomain: (domain: Schema<"DomainRequest">) =>
    send<Schema<"SavedDomain">>("POST", "/domains", domain),
  ontologies: (signal?: AbortSignal) =>
    get<Schema<"SavedOntology">[]>("/ontologies", undefined, signal),
};

export function useDomains() {
  return useQuery({
    queryKey: ["domains"],
    queryFn: ({ signal }) => libraryApi.domains(signal),
    retry: false,
  });
}

export function useSavedOntologies() {
  return useQuery({
    queryKey: ["saved-ontologies"],
    queryFn: ({ signal }) => libraryApi.ontologies(signal),
    retry: false,
  });
}
