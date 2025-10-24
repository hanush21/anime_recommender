"use client";

import { Card, CardContent } from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import type { RecommenderItem } from "@/lib/types";

type Props = { items: RecommenderItem[] };

export default function RecommendationsTable({ items }: Props) {
    return (
        <Card className="w-full">
            <CardContent className="p-0">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Nombre</TableHead>
                            <TableHead className="text-right">Co-relación</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {items.map((it, idx) => (
                            <TableRow key={it.anime_id ?? `${it.name}-${idx}`}>
                                <TableCell className="font-medium">{it.name}</TableCell>
                                <TableCell className="text-right">
                                    {it.correlation.toFixed(3)}
                                </TableCell>
                            </TableRow>
                        ))}
                        {items.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={2} className="text-center py-8 text-sm text-muted-foreground">
                                    Sin resultados.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
