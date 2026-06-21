import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

def gerar_graficos():
    caminho_csv = 'resultados/dados_finais.csv'
    if not os.path.exists(caminho_csv):
        print("Arquivo CSV não encontrado. Rode o main.py primeiro.")
        return

    df = pd.read_csv(caminho_csv)
    
    # Removemos a baseline NONE para focar apenas nos compressores
    df_algos = df[df['algoritmo'] != 'NONE']

    sns.set_theme(style="whitegrid")
    
    # ---------------------------------------------------------
    # Figura 1: Taxa de Compressão (Por dataset)
    # ---------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    df_rep = df_algos[df_algos['arquivo'] == 'repetitivo.txt'].sort_values('taxa', ascending=False)
    sns.barplot(data=df_rep, x='taxa', y='algoritmo', ax=axes[0], color='skyblue')
    axes[0].set_title('Taxa de Compressão - Repetitivo')
    axes[0].set_xlabel('Taxa (x:1)')
    axes[0].set_ylabel('')
    for i, v in enumerate(df_rep['taxa']):
        axes[0].text(v, i, f" {v:.1f}:1", va='center')

    df_ale = df_algos[df_algos['arquivo'] == 'aleatorio.bin'].sort_values('taxa', ascending=False)
    sns.barplot(data=df_ale, x='taxa', y='algoritmo', ax=axes[1], color='salmon')
    axes[1].set_title('Taxa de Compressão - Aleatório')
    axes[1].set_xlabel('Taxa (x:1)')
    axes[1].set_ylabel('')
    # Ajusta limite X para aleatório para que o texto não fique colado no fim
    axes[1].set_xlim(0, 1.2)
    for i, v in enumerate(df_ale['taxa']):
        axes[1].text(v, i, f" {v:.2f}:1", va='center')
        
    plt.tight_layout()
    plt.savefig('resultados/fig1_taxa_compressao.png')
    plt.close()

    # ---------------------------------------------------------
    # Figura 2: Velocidade de Compressão
    # ---------------------------------------------------------
    df_vel = df_algos.groupby('algoritmo')['throughput_mbps'].mean().reset_index().sort_values('throughput_mbps', ascending=False)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_vel, x='throughput_mbps', y='algoritmo', color='lightgreen')
    plt.title('Velocidade de Compressão (Média)')
    plt.xlabel('Velocidade (MB/s)')
    plt.ylabel('')
    for i, v in enumerate(df_vel['throughput_mbps']):
        plt.text(v, i, f" {v:.1f} MB/s", va='center')
    plt.tight_layout()
    plt.savefig('resultados/fig2_velocidade_compressao.png')
    plt.close()

    # ---------------------------------------------------------
    # Figura 3: Velocidade de Descompressão
    # ---------------------------------------------------------
    df_dvel = df_algos.groupby('algoritmo')['throughput_decomp_mbps'].mean().reset_index().sort_values('throughput_decomp_mbps', ascending=False)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_dvel, x='throughput_decomp_mbps', y='algoritmo', color='mediumpurple')
    plt.title('Velocidade de Descompressão (Média)')
    plt.xlabel('Velocidade (MB/s)')
    plt.ylabel('')
    for i, v in enumerate(df_dvel['throughput_decomp_mbps']):
        plt.text(v, i, f" {v:.1f} MB/s", va='center')
    plt.tight_layout()
    plt.savefig('resultados/fig3_velocidade_descompressao.png')
    plt.close()

    # ---------------------------------------------------------
    # Figura 4: Bubble Chart (Trade-off)
    # ---------------------------------------------------------
    plt.figure(figsize=(10, 6))
    # Para o bubble chart, usamos o arquivo repetitivo, onde o trade-off é mais claro
    df_bubble = df_algos[df_algos['arquivo'] == 'repetitivo.txt']
    
    sns.scatterplot(
        data=df_bubble,
        x='taxa',
        y='throughput_mbps',
        hue='algoritmo',
        size='tamanho_final',
        sizes=(200, 2000),
        legend=False,
        alpha=0.6,
        palette='tab10'
    )
    plt.xscale('log')
    plt.yscale('log')
    plt.title('Trade-off: Taxa x Velocidade (Tamanho da bolha = Tamanho Final)')
    plt.xlabel('Taxa de Compressão (x:1) - Log')
    plt.ylabel('Velocidade (MB/s) - Log')
    
    for i, row in df_bubble.iterrows():
        plt.text(row['taxa'], row['throughput_mbps'], row['algoritmo'], 
                 ha='center', va='center', fontsize=11, weight='bold', color='black')

    plt.tight_layout()
    plt.savefig('resultados/fig4_bubble_chart.png')
    plt.close()

    # ---------------------------------------------------------
    # Figura 5: Ranking Geral
    # ---------------------------------------------------------
    df_rank = df_algos.groupby('algoritmo').agg({'taxa': 'mean', 'throughput_mbps': 'mean'}).reset_index()
    df_rank['score'] = df_rank['taxa'] * np.log10(df_rank['throughput_mbps'])
    df_rank = df_rank.sort_values('score', ascending=False)
    
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_rank, x='score', y='algoritmo', color='gold')
    plt.title('Ranking Geral (Score = Taxa * log10(Velocidade))')
    plt.xlabel('Score')
    plt.ylabel('')
    
    max_score = df_rank['score'].max()
    for i, (algo, score) in enumerate(zip(df_rank['algoritmo'], df_rank['score'])):
        plt.text(score + (max_score*0.01), i, f"{score:.0f} pts", va='center', weight='bold')
        plt.text(max_score*0.02, i, f"{i+1}º", va='center', weight='bold', color='black', ha='left', fontsize=14)
        
    plt.tight_layout()
    plt.savefig('resultados/fig5_ranking_geral.png')
    plt.close()

    print("Novos gráficos gerados com sucesso em 'resultados/'.")

if __name__ == "__main__":
    gerar_graficos()
