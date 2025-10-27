"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent } from "@/components/ui/card";
import axios from "axios";
import type { RecommenderItem } from "@/lib/types";

type SeenPickerProps = {
    onResults: (items: RecommenderItem[]) => void;
};

export default function SeenPicker({ onResults }: SeenPickerProps) {
    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState("");
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [selected, setSelected] = useState<string[]>([]);
    const [submitting, setSubmitting] = useState(false);
    const [loadingSug, setLoadingSug] = useState(false);
    const debounceRef = useRef<number | null>(null);

    // cargar sugerencias remotas cuando el usuario escribe
    useEffect(() => {
        if (debounceRef.current) window.clearTimeout(debounceRef.current);
        if (search.trim().length < 2) {
            setSuggestions([]);
            return;
        }
        setLoadingSug(true);
        debounceRef.current = window.setTimeout(async () => {
            try {
                const res = await axios.get<RecommenderItem[]>("/api/recommenders_anime/by-seen", {
                    params: { q: search.trim(), topk: 50 },
                });
                const names = (res.data ?? []).map((r) => r.name);
                setSuggestions(names);
            } catch {
                setSuggestions([]);
            } finally {
                setLoadingSug(false);
            }
        }, 350); // debounce
    }, [search]);

    const filtered = useMemo(() => suggestions, [suggestions]);

    const toggle = (name: string) => {
        setSelected((prev) =>
            prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name]
        );
    };

    const clearAll = () => setSelected([]);

    const submit = async () => {
        if (selected.length === 0) return;
        setSubmitting(true);
        try {
            const res = await axios.post<RecommenderItem[]>(
                "/api/recommenders/by-seen",
                { seen_names: selected, topk: 10 }
            );
            onResults(res.data ?? []);
            setOpen(false);
        } catch (e) {
            console.error(e);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Card>
            <CardContent className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                    <div className="text-sm font-medium">Recomendación por vistos</div>
                    <Dialog open={open} onOpenChange={setOpen}>
                        <DialogTrigger asChild>
                            <Button size="sm" variant="default">Elegir animes vistos</Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-xl">
                            <DialogHeader>
                                <DialogTitle>Selecciona los animes que ya viste</DialogTitle>
                            </DialogHeader>

                            <div className="space-y-3">
                                <Input
                                    placeholder="Busca título (mín. 2 letras)…"
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                />

                                {selected.length > 0 && (
                                    <>
                                        <div className="flex flex-wrap gap-2">
                                            {selected.slice(0, 10).map((s) => (
                                                <Badge key={s} variant="secondary" className="cursor-pointer" onClick={() => toggle(s)}>
                                                    {s}
                                                </Badge>
                                            ))}
                                            {selected.length > 10 && (
                                                <Badge variant="outline">+{selected.length - 10} más</Badge>
                                            )}
                                        </div>
                                        <div className="flex justify-end">
                                            <Button variant="ghost" size="sm" onClick={clearAll}>Limpiar selección</Button>
                                        </div>
                                    </>
                                )}

                                <Separator />

                                <div className="text-xs text-muted-foreground">
                                    {loadingSug ? "Buscando…" : `Resultados (${filtered.length})`}
                                </div>
                                <ScrollArea className="h-72 rounded-md border p-3">
                                    <div className="grid grid-cols-1 gap-2">
                                        {filtered.map((name) => {
                                            const checked = selected.includes(name);
                                            return (
                                                <label key={name} className="flex items-center gap-3 cursor-pointer">
                                                    <Checkbox checked={checked} onCheckedChange={() => toggle(name)} />
                                                    <span className="text-sm">{name}</span>
                                                </label>
                                            );
                                        })}
                                        {!loadingSug && filtered.length === 0 && (
                                            <div className="text-sm text-muted-foreground">Sin coincidencias.</div>
                                        )}
                                    </div>
                                </ScrollArea>

                                <div className="flex items-center justify-end gap-2 pt-2">
                                    <Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button>
                                    <Button onClick={submit} disabled={selected.length === 0 || submitting}>
                                        {submitting ? "Generando…" : "Ver recomendaciones"}
                                    </Button>
                                </div>
                            </div>
                        </DialogContent>
                    </Dialog>
                </div>

                <p className="text-xs text-muted-foreground">
                    Elige varios títulos; generaremos recomendaciones basadas en tu selección.
                </p>
            </CardContent>
        </Card>
    );
}
