#!/usr/bin/env python3
import os, gc, csv, bz2, math, zlib, lzma, time, hashlib, statistics, shutil
import lz4.frame, zstandard

TAMANHO  = 10 * 1024 * 1024
REPETICOES = 5
CSV_SAIDA  = "resultados/dados_finais.csv"

COR = dict(
    RST="\033[0m", NEG="\033[1m", CINZA="\033[90m", VERM="\033[91m",
    VERDE="\033[92m", AMAR="\033[93m", CIANO="\033[96m", AM_NEG="\033[1;93m",
)

compressor_zstd = zstandard.ZstdCompressor()
descompressor_zstd = zstandard.ZstdDecompressor()

# (nome, comprimir, descomprimir, cor)
MOTORES = [
    ("NONE", bytes,              bytes,              COR["CINZA"]),
    ("ZLIB", zlib.compress,      zlib.decompress,    COR["CIANO"]),
    ("BZ2",  bz2.compress,       bz2.decompress,     COR["CIANO"]),
    ("LZMA", lzma.compress,      lzma.decompress,    COR["CIANO"]),
    ("LZ4",  lz4.frame.compress, lz4.frame.decompress, COR["VERDE"]),
    ("ZSTD", compressor_zstd.compress,       descompressor_zstd.decompress,     COR["VERDE"]),
]


def gerar_dataset() -> dict[str, bytes]:
    os.makedirs("dados", exist_ok=True)

    frase = b"O rato roeu a roupa do rei de Roma. "
    repetitivo = (frase * (TAMANHO // len(frase) + 1))[:TAMANHO]
    aleatorio  = os.urandom(TAMANHO)

    for nome, dados in [("dados/repetitivo.txt", repetitivo), ("dados/aleatorio.bin", aleatorio)]:
        with open(nome, "wb") as f:
            f.write(dados)

    print(f"\n{COR['VERDE']}[DATASET]{COR['RST']} 2 arquivos de {TAMANHO/(1024*1024):.0f} MiB gerados")
    return {"repetitivo.txt": repetitivo, "aleatorio.bin": aleatorio}


def sha256(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def fmt_tempo(seg: float) -> str:
    if seg < 1e-3:  return f"{seg*1e6:8.2f} µs"
    if seg < 1.0:   return f"{seg*1e3:8.2f} ms"
    return f"{seg:8.2f} s "


def fmt_velocidade(mbps: float, baseline: bool) -> str:
    if baseline:    return f"{COR['CINZA']}     ∞ MB/s{COR['RST']}"
    if mbps > 1000: return f"{COR['AM_NEG']}{mbps:8.1f} MB/s{COR['RST']}"
    return f"{mbps:8.1f} MB/s"


def laudo(tam_orig: int, tam_final: int) -> str:
    largura_coluna = 34
    if tam_final > tam_orig:
        pct = ((tam_final / tam_orig) - 1.0) * 100
        if round(pct) == 0:
            txt = "⚖️ Sem alteração de tamanho"
            cor, fim = COR["CINZA"], COR["RST"]
        else:
            txt = f"⚠️ CRESCEU {pct:.0f}%"
            cor, fim = COR["VERM"], COR["RST"]
    elif tam_final == tam_orig or (tam_final > 0 and tam_orig / tam_final < 1.02):
        txt = "⚖️ Sem alteração de tamanho"
        cor, fim = COR["CINZA"], COR["RST"]
    else:
        txt = f"📉 {int(tam_orig / tam_final)} vezes menor"
        cor, fim = COR["VERDE"], COR["RST"]
    return f"{cor}({txt}){fim}".ljust(largura_coluna + len(cor) + len(fim))


def benchmark(nome_arq: str, dados: bytes) -> list[dict]:
    tam_orig = len(dados)
    tam_mb   = tam_orig / (1024 * 1024)
    hash_ref = sha256(dados)
    resultados = []

    RESETAR_COR, NEGRITO = COR["RST"], COR["NEG"]
    print(f"\n{'═'*100}")
    print(f"  {NEGRITO}📂 {nome_arq}  ({tam_mb:.1f} MiB)  SHA-256: {hash_ref[:16]}…{RESETAR_COR}")
    print(f"{'═'*100}")
    print(f"  {'Algoritmo':<10} │ {'Taxa':>12}  {'Laudo':<28} │ {'Compressão':>14} │ {'Descompressão':>14} │ {'CPU':>12}")
    print(f"{'─'*100}")

    for nome, comprimir, descomprimir, cor in MOTORES:
        is_none = nome == "NONE"

        comprimir(dados)  # warmup
        descomprimir(comprimir(dados))

        t_comp, t_decomp = [], []
        tam_final = 0

        for i in range(REPETICOES):
            gc.disable()
            t0 = time.process_time()
            comprimido = comprimir(dados)
            t1 = time.process_time()
            gc.enable()
            t_comp.append(t1 - t0)
            tam_final = len(comprimido)

            gc.disable()
            t2 = time.process_time()
            resultado = descomprimir(comprimido)
            t3 = time.process_time()
            gc.enable()
            t_decomp.append(t3 - t2)

            if i == 0 and sha256(resultado) != hash_ref:
                raise Exception(f"INTEGRIDADE FALHOU: {nome}")

        mediana_tempo_comp = statistics.median(t_comp)
        mediana_tempo_decomp = statistics.median(t_decomp)
        taxa_mbps_compressao  = tam_mb / mediana_tempo_comp if mediana_tempo_comp > 0 else float('inf')
        taxa_mbps_descompressao  = tam_mb / mediana_tempo_decomp if mediana_tempo_decomp > 0 else float('inf')
        taxa  = tam_orig / tam_final if tam_final > 0 else 1.0

        print(f"  {cor}{nome:<10}{RESETAR_COR} │ {COR['AMAR']}{taxa:10.2f}:1{RESETAR_COR}  {laudo(tam_orig, tam_final)} "
              f"│ {fmt_velocidade(taxa_mbps_compressao, is_none)} │ {fmt_velocidade(taxa_mbps_descompressao, is_none)} │ {fmt_tempo(mediana_tempo_comp + mediana_tempo_decomp)}")

        resultados.append(dict(
            algoritmo=nome, arquivo=nome_arq,
            tamanho_original=tam_orig, tamanho_final=tam_final,
            taxa=round(taxa, 4), throughput_mbps=round(taxa_mbps_compressao, 2),
            throughput_decomp_mbps=round(taxa_mbps_descompressao, 2),
        ))

    resumo(resultados, nome_arq)
    return resultados


def resumo(resultados: list[dict], nome_arq: str) -> None:
    algoritmos_validos = [r for r in resultados if r["algoritmo"] != "NONE"]
    if not algoritmos_validos: return

    menor  = min(algoritmos_validos, key=lambda r: r["tamanho_final"])
    rapido = max(algoritmos_validos, key=lambda r: r["throughput_mbps"])
    score  = lambda r: r["taxa"] * math.log10(r["throughput_mbps"]) if r["throughput_mbps"] > 0 else 0
    melhor_equilibrio  = max(algoritmos_validos, key=score)

    NEGRITO, RESETAR_COR = COR["NEG"], COR["RST"]
    print(f"\n  {NEGRITO}┌─ Resumo: {nome_arq} ─────────────────────────────┐{RESETAR_COR}")
    print(f"  │ 👑 Menor tamanho:    {COR['VERDE']}{menor['algoritmo']:<6}{RESETAR_COR}  (taxa {menor['taxa']:.2f}:1)")
    print(f"  │ ⚡ Mais rápido:      {COR['AMAR']}{rapido['algoritmo']:<6}{RESETAR_COR}  ({rapido['throughput_mbps']:.1f} MB/s)")
    print(f"  │ ⚖️  Melhor equilíbrio: {COR['CIANO']}{melhor_equilibrio['algoritmo']:<6}{RESETAR_COR}  (score {score(melhor_equilibrio):.2f})")
    print(f"  {NEGRITO}└──────────────────────────────────────────────────┘{RESETAR_COR}")


def exportar_csv(resultados: list[dict]) -> None:
    os.makedirs("resultados", exist_ok=True)
    colunas = ["algoritmo", "arquivo", "tamanho_original", "tamanho_final",
               "taxa", "throughput_mbps", "throughput_decomp_mbps"]
    with open(CSV_SAIDA, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        w.writerows(resultados)
    print(f"\n{COR['VERDE']}[CSV]{COR['RST']} → {CSV_SAIDA}")


def main() -> None:
    if os.path.exists("resultados"):
        shutil.rmtree("resultados")
    os.makedirs("resultados", exist_ok=True)

    NEGRITO, RESETAR_COR = COR["NEG"], COR["RST"]
    print(f"\n{NEGRITO}{'═'*100}{RESETAR_COR}")
    print(f"  {NEGRITO}BENCHMARK DE COMPRESSÃO — Trade-off: Throughput (CPU) vs Taxa de Compressão (Espaço){RESETAR_COR}")
    print(f"  Repetições: {REPETICOES}  |  Métrica: Mediana  |  Timer: process_time()  |  GC: isolado")
    print(f"{NEGRITO}{'═'*100}{RESETAR_COR}")

    dataset = gerar_dataset()
    todos = []
    for nome, dados in dataset.items():
        todos.extend(benchmark(nome, dados))
    exportar_csv(todos)
    print(f"\n{COR['VERDE']}[FIM]{COR['RST']} Benchmark concluído.\n")


if __name__ == "__main__":
    main()
