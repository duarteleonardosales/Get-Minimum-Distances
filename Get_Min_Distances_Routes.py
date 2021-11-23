# CÁLCULO AUTOMÁTICO DAS MENORES DISTANCIAS ENTRE IMÓVEIS E POLOS VALORIZANTES

import numpy as np
import tkinter
from tkinter import ttk
import osmnx as ox
from osmnx import utils_graph
import networkx as nx
import utm
import fastkml
import shapely
import pandas as pd
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import matplotlib
from pandastable import Table
from scipy.stats import pearsonr
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk) #https://matplotlib.org/3.1.0/gallery/user_interfaces/embedding_in_tk_sgskip.html
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

#CONFIGURAÇÕES
#-------------------------------------------------------
matplotlib.use('Agg') # PARA NÃO INICIAR O SHOW DAS FIGS
ox.config(use_cache=True, log_console=True)
path_png = '../ROTAS'
path_tabelas = '../TABELAS'

#-------------------------------------------------------

# INTERFACE GRAFICA
# CRIANDO O ROOT...É O SUBSTRATO DO PROJETO, SOBRE O QUAL SERÃO LANÇADOS OS DEMAIS ELEMENTOS.
#-------------------------------------------------------
root = tkinter.Tk()
root.title('GMD - GetMinDistances - By: Eng. Leonardo Sales Duarte')
root.geometry('600x300')
root.minsize(1300,600)
root.maxsize(1300,600)
#-------------------------------------------------------

#CRIANDO FILE_DIALOGS
#-------------------------------------------------------
def ask_file_imoveis():
    global path_imoveis
    path_imoveis = filedialog.askopenfilename()
    return path_imoveis

def ask_file_valorizante():
    global path_valorizante
    path_valorizante = filedialog.askopenfilename()
    return path_valorizante

def ask_file_valores(evento='<Return>'):
    global path_valores, valores_totais
    nome_da_coluna = entry3.get()
    path_valores = filedialog.askopenfilename()

    amostra_imoveis = pd.DataFrame()
    amostra_imoveis = pd.read_csv(path_valores)
    valores_totais = amostra_imoveis[nome_da_coluna].tolist()
    print(valores_totais)
    print(evento)
    #print(entry3.get())
#-------------------------------------------------------
# MSG SOBRE RESULTADOS
def message_save():
    return messagebox.showinfo('Diretório dos resultados',message=f'Tabelas e Imagens foram salvas em:\n{path_tabelas} e\n{path_png}')
#-------------------------------------------------------

# CRIANDO LABELS, BUTTONS, ENTRYS...
label_frame_1 = tkinter.LabelFrame(root, text='BUSCAR ARQUIVOS', height=110, width=790, font='Arial 12')
label_frame_1.place(anchor='nw',x=5, y=5)
#--------------------------------
label1 = tkinter.Label(root, text='IMÓVEIS COLETADOS', font=('ARIAL', 12))
label1.place(anchor='nw',x=25, y=35)
button1 = tkinter.Button(root, text='BUSCAR .KML', font=('ARIAL', 10), command = ask_file_imoveis)
button1.place(anchor='nw',x=210, y=35)
#--------------------------------
label2 = tkinter.Label(root, text='POLO VALORIZANTE', font=('ARIAL', 12))
label2.place(anchor='nw',x=370, y=35)
button2 = tkinter.Button(root, text='BUSCAR .KML', font=('ARIAL', 10), command=ask_file_valorizante)
button2.place(anchor='nw',x=670, y=35)
#--------------------------------
label3 = tkinter.Label(root, text='INSERIR NOME DA COLUNA DOS VALORES:', font=('ARIAL', 12))
label3.place(anchor='nw',x=25, y=80)
#--------------------------------
entry3 = tkinter.Entry(root)
entry3.place(anchor='nw',x=380, y=80)
entry3.bind('<Return>', ask_file_valores)
#--------------------------------
var_rb = tkinter.StringVar()

rb1 = tkinter.Radiobutton(root, text='Lines/Polylines', variable=var_rb, value='0')
rb1.place(anchor='nw',x=550, y=25)

rb2 = tkinter.Radiobutton(root, text='Points', variable=var_rb, value='1')
rb2.place(anchor='nw',x=550, y=45)

#tabela e frame da tabela
label_frame_tab = tkinter.LabelFrame(root, text='TABELA', height=600, width=400, font ="Arial 12")
label_frame_tab.place(anchor='nw',x=800, y=5)
tabela = Table(label_frame_tab, height=500, width=400,
                rows = 20, cols = 5, showtoolbar = True,
                showstatusbar = True, editable = True, enable_menus = True) # A TABELA PRECISA ESTAR SOBRE UM FRAME
tabela.show()
#--------------------------------
#frame das imagens
label_frame_fig = tkinter.LabelFrame(root, text='ROTAS', height=465, width=500, font ="Arial 12")
label_frame_fig.grid(sticky='E')
label_frame_fig.place(anchor='nw',x=5, y=125)
#--------------------------------
#frame do text
label_frame_text = tkinter.LabelFrame(root, text='PROCESSAMENTO', height=465, width=280, font ="Arial 12")
label_frame_text.place(anchor='nw',x=515, y=125)
#--------------------------------
# text
txt = tkinter.Text(root, width = 33, height = 27)
txt.place(anchor='nw',x=520, y=150)
#--------------------------------

# FUNÇÃO PARA LIMPAR O TXT
def clear_txt():
    txt.delete(1.0, tkinter.END)
#--------------------------------

# DETERMINAR AS COORDENADAS UTM DE TODOS OS PONTOS PESQUISADOS
# REFERENCIAS https://medium.com/@wwaryan/the-definite-only-guide-to-fastkml-58b8e19b8454 E https://gis.stackexchange.com/questions/343265/extracting-coordinates-of-placemark-from-kml-using-fastkml

#CRIAR UMA FUNÇÃO QUE PEGA AS FEATURES REFERENTES AOS PONTOS E LINHAS DO KML FORNECIDO PELO USUÁRIO
def getkml_features(kml_path):
    doc = open(kml_path)
    doc_read = doc.read().encode() #se tirar o encode vai dar erro.
    k = fastkml.KML()
    k.from_string(doc_read)

    feature_doc = list(k.features()) # representa o document
    feature_place = list(feature_doc[0].features()) # representa folder or placemarks

    #SE HOUVER FOLDER NA ESTRUTURA DO KML, TEM QUE PERCORRER AQUI
    if isinstance(feature_place[0], fastkml.kml.Folder):
        feature_place = list(feature_place[0].features())  # representa os placemarks

    return feature_place #é uma lista com todos placemarks...linhas/pontos

# PEGAR AS COORDENADAS X e Y...tem que usar .geometry.x ou y
# NO CASO DE PONTOS
def get_coord_points(csv_name, kml_path):

    lat_list = []
    long_list = []
    name_list = []
    feature_place = getkml_features(kml_path)
    for i in range( len( feature_place ) ):

        # FAZER VERIFICAÇÃO SE O FEATURE_PLACE É UM PONTO...PARA GARANTIR QUE SÓ PONTOS SERÃO LIDOS NESSA FUNÇÃO
        if isinstance( feature_place[i].geometry, shapely.geometry.point.Point ):

            lat_list.append( feature_place[i].geometry.y )
            long_list.append( feature_place[i].geometry.x )
            name_list.append(feature_place[i].name) #adicionando os identificadores de cada elemento

    # CONVERTER LAT, LONG PARA UTM ===================================
    utm_list = utm.from_latlon( np.array(lat_list).flatten(), np.array(long_list).flatten() ) #GERA UM NUMPY ARRAY COM TODOS OS E e N = [0] e [1]
    utm_list = np.array(utm_list).tolist()

    #DELETAR OS DOIS ULTIMOS ELEMENTOS = ZONA Nº E LETRA...NAO FAZEM SENTIDO PARA O ESTUDO
    #print(f'letra e numero : {utm_list[-1]} , {utm_list[-2]}')
    global zona_numero, zona_letra
    zona_numero = utm_list[-2]
    zona_letra = utm_list[-1]
    del utm_list[-1]
    del utm_list[-1]
    #=================================================================

    # GERAR UM DATAFRAME COM PANDAS E UM CSV DOS PONTOS

    data_pontos = pd.DataFrame()
    data_pontos['ID_NAME'] = name_list
    data_pontos['E'] = utm_list[0]
    data_pontos['N'] = utm_list[1]

    data_pontos.to_csv(f'{path_tabelas}/{csv_name}.csv')

    return data_pontos



# PEGAR AS COORDENADAS X e Y
# NO CASO DE LINHAS

def get_coord_lines(csv_name, kml_path):

    name_list = []
    data_linhas_list = []
    feature_place = getkml_features(kml_path)
    for i in range( len( feature_place ) ):
        long_list = []
        lat_list = []
        coord_line_list = []

        # FAZER VERIFICAÇÃO SE O FEATURE_PLACE É UM PONTO...PARA GARANTIR QUE SÓ LINES SERÃO LIDOS NESSA FUNÇÃO
        if isinstance( feature_place[i].geometry, shapely.geometry.linestring.LineString ):

            name_list.append(feature_place[i].name) #adicionando os identificadores de cada elemento
            str_coord_line = feature_place[i].geometry.to_wkt() #manipular essa string para extrair somente as coordenadas
            str_coord_line = str_coord_line.replace(str_coord_line[0:11],'') #aqui replace os 11 primeiros caracteres (LINESTRING ) por nada ''. A DICA ESTÁ EM https://stackoverflow.com/questions/11806559/removing-first-x-characters-from-string
            #print(str_coord_line)
            str_coord_line = str_coord_line.replace('(', '')
            str_coord_line = str_coord_line.replace(')', '')
            str_coord_line = str_coord_line.replace(', ', ',')
            str_coord_line = str_coord_line.replace(' ', ',')


            # O str_coord_line É UMA STRING, COM PARES ORDENADOS DE PONTOS QUE COMPOEM A LINHA...VAMOS AGORA COLOCAR ISSO EM FORMA NUMERICA E NUMA LISTA
            # NA LISTA coord_line_list OS NUMEROS COM INDEX PARES SAO LONG....IMPAR SAO LAT
            i_acumluado = ''

            for i2 in str_coord_line:
                if i2 != ',':
                    i_acumluado = i_acumluado + i2
                if i2 == ',':
                    coord_line_list.append(float(i_acumluado)) #INSERIR UMA COORDENADA TODA VEZ QUE ACHAR O ','
                    i_acumluado = ''
            coord_line_list.append(float(i_acumluado)) #ESSE ACUMULADO FORA DO LOOP É A ULTIMA COORDENADA QUE NAO HAVIA SIDO INSERIDA

            #print(coord_line_list)

            # SEPARAR LONG---PARES
            long_list = [ i for i in coord_line_list if coord_line_list.index(i)%2 == 0 ]

            # SEPARAR LAT---IMPAR
            lat_list = [ i for i in coord_line_list if coord_line_list.index(i)%2 != 0 ]

            # CONVERTER LAT, LONG PARA UTM
            utm_list = utm.from_latlon(np.array(lat_list), np.array(long_list) ) #GERA UM NUMPY ARRAY COM TODOS OS E e N = [0] e [1]
            utm_list = np.array(utm_list).tolist()

            #DELETAR OS DOIS ULTIMOS ELEMENTOS = ZONA Nº E LETRA...NAO FAZEM SENTIDO PARA O ESTUDO
            del utm_list[-1]
            del utm_list[-1]
            #=================================================================

            # GERAR UM DATAFRAME COM PANDAS E UM CSV DOS PONTOS
            #print(f'utm: {utm_list[0]}')
            data_linhas = pd.DataFrame()
            data_linhas['ID_NAME'] = len(long_list)*list([name_list[-1]])#É SEMPRE O ULTIMO A TER SIDO ADICIONADO
            data_linhas['E'] = utm_list[0]
            data_linhas['N'] = utm_list[1]
            data_linhas_list.append(data_linhas)
            data_linhas.to_csv(f'{path_tabelas}/{csv_name}_{name_list[-1]}.csv')

            del data_linhas, utm_list, str_coord_line, i_acumluado, i2
    return data_linhas_list

# DISTANCIA MINIMA ENTRE DOIS PONTOS - DIST. EUCLIDIANA
def dist_min_point(x1,y1,x2,y2):
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

# DETERMINAR O CENTROIDE DE TODOS OS PONTOS DOS IMÓVEIS PARA DEFINIR O LOCAL DO MAPA QUE VAI SER CONSIDERADO NO OSMNX
def getcentroid(list_x, list_y):
    centroide_x = sum(list_x)/len(list_x)
    centroide_y = sum(list_y)/len(list_y)
    centroide = (centroide_x, centroide_y)
    return centroide

# PEGAR A DIST MAX ENTRE O CENTROIDE E OS IMOVEIS...PARA DETERMINAR A AMPLITUDE DO GRAFICO.
def maxdist_centroide_to_imovel(centroide_x, centroide_y,list_x, list_y):
    lista_dist_cent_to_imovel = []
    for qtd in range(len(list_x)): #len list_x = len list_y
        dist = dist_min_point( centroide_x, centroide_y, list_x[qtd], list_y[qtd] )
        lista_dist_cent_to_imovel.append(dist)

    print(f'está sendo considerada uma dist de {max(lista_dist_cent_to_imovel)+500}')
    return max(lista_dist_cent_to_imovel)+500


#DISTANCIA MININA ENTRE PONTO E UMA RETA...(DEFINIDA ENTRE DOIS PONTOS X1,Y1 E X2,Y2; XP E YP SÃO AS COORDENADAS DO PONTO (IMOVEL)
def dist_min_point_reta(x1,y1,x2,y2,xp,yp):
    # o ponto 2 é sempre aquele com E maior que o 1
    if x2<x1:
        x1,y1,x2,y2 = x2,y2,x1,y1 #CASO O USUARIO TENHA INFORMADO OS PONTOS NA ORDEM ERRADA...INVERTER OS PONTOS

    #---
    # PRECISO DAS COORDENADAS DO PONTO PROJETADO.
    # DEPOIS, AO FINAL VAMOS TESTAR SE A PROJEÇÃO ESTÁ DENTRO OU FORA DO SEGMENTO DA RETA
    if y1 == y2:
        yp_proj = y1
        xp_proj = xp

    if x1 == x2:
        yp_proj = yp
        xp_proj = x1

    if y1!=y2 and x1!=x2:

        # tg e b da line
        # tang = cateto oposto / cateto adjacente
        # y=ax+b --> b = y-ax; em que a = tg
        tg = (y2 - y1) / (x2 - x1)
        # b = y1 - (tg * x1)

        # COEFICIENTE ANGULAR DA RETA PERPENDICULAR À LINE
        tg_90 = -1 / tg

        # Equação para X do ponto de intersecçao entre as retas perpendiculares
        xp_proj = (yp - y1 + tg * x1 - tg_90 * xp) / (tg - tg_90)  # VER FIGURA NA PASTA PARA MAIS DETALHES
        yp_proj = (y1 - tg_90 * (xp_proj - x1))

    #---
    # HÁ TRES SITUAÇÕES...UMA QUE O PONTO ESTÁ NO ESCOPO DA RETA....NESSE CASO, A DIST PERPENDICULAR É A MIN. DESEJADA.
    # OUTRA ONDE ELE ESTÁ FORA DO ESCOPO DA RETA...DAI A DIST. MIN SERÁ UMA DIST. INCLINADA ATE UMA DAS EXTREMIDADES.
    # EQUAÇÃO PARAMETRICA DE UMA RETA ax + by + c = 0
    a = y1-y2
    b = x2-x1
    c = x1*y2 - x2*y1

    dist_p_r = np.abs( a * xp + b * yp + c ) / (np.sqrt(a**2+b**2)) # SE A PROJEÇÃO ESTIVER DENTRO DO SEGMENTO DE RETA

    # DISTANCIAS NECESSÁRIAS (DIST. INCLINADAS, CASO A PROJEÇÃO ESTEJA FORA DO SEGMENTO DA RETA)

    dist_imovel_1 = dist_min_point(xp, yp, x1, y1)
    dist_imovel_2 = dist_min_point(xp, yp, x2, y2)

    # VERIFICAR SE O PONTO PROJETADO ESTÁ FORA OU DENTRO DO ESCOPO DO SEGMENTO DE RETA
    # SE ESTIVER, ENTAO A DIST MIN É A DIST ENTRE PONTO E RETA...FORMANDO 90 GRAUS
    # SE NAO ESTIVER, A DIST MIN É A DIST PARA ALGUM DOS PONTOS DE EXTREMIDADE DO SEGMENTO (1 OU 2)

    # 1)
    if xp_proj < x1 and xp_proj < x2 :
        return (dist_imovel_1, x1, y1)

    # 2)
    if xp_proj > x1 and xp_proj > x2 :
        return (dist_imovel_2, x2, y2)

    # 3)
    if x1 < xp_proj < x2:
        return (dist_p_r, xp_proj, yp_proj)

    #---
    # VER QUEM É MAIOR...Y2 OU Y1
    if y2>y1:
        tupla_se_menor = (dist_imovel_1, x1, y1)
        tupla_se_maior = (dist_imovel_2, x2, y2)
        tupla_se_entre = (dist_p_r, xp_proj, yp_proj)

    if y1>y2:
        tupla_se_menor = (dist_imovel_2, x2, y2)
        tupla_se_maior = (dist_imovel_1, x1, y1)
        tupla_se_entre = (dist_p_r, xp_proj, yp_proj)

    # 4)
    if x1 == xp_proj == x2:

        if yp_proj < y1 and yp_proj < y2:
            return tupla_se_menor

        if yp_proj > y1 and yp_proj > y2:
            return tupla_se_maior

        if min([y1, y2]) < yp_proj < max([y1, y2]):
            return tupla_se_entre

    #---

global g, g_type
g = 0
g_type = ''
#---------------------------------------------

def calc_min_routes_nx(origem, destino): #origem e destino sao tuplas
    #global zona_numero, zona_letra

    data_imoveis = get_coord_points('Avaliados', path_imoveis)  # essa função retorna o dataframe
    E = data_imoveis['E']
    N = data_imoveis['N']
    E_N_centroide=getcentroid(E, N)
    dist_max = maxdist_centroide_to_imovel(E_N_centroide[0], E_N_centroide[1], E, N)
    lat_long_centroide = utm.to_latlon(E_N_centroide[0],E_N_centroide[1],zona_numero,zona_letra) #tupla lat_long
    global g, g_type

    if type(g) != g_type: #PARA NAO FICAR BAIXANDO TODA VEZ O MODELO NO OSMNX
        g = ox.graph_from_point(lat_long_centroide, dist=dist_max, network_type='drive') #entrada não é em UTM...entao tem que voltar para lat long
        #---
        g = ox.utils_graph.get_largest_component(g, strongly=True)
        #---
        g_type = type(g)
        print(f'CARREGOU G')

    lat_long_origem = utm.to_latlon(origem[0],origem[1],zona_numero,zona_letra) #tupla lat_long
    lat_long_destino = utm.to_latlon(destino[0],destino[1],zona_numero,zona_letra) #tupla lat_long

    # PEGAR O NÓ MAIS PRÓXIMO
    start_node = ox.nearest_nodes(g, lat_long_origem[1], lat_long_origem[0])
    end_node = ox.nearest_nodes(g, lat_long_destino[1], lat_long_destino[0])

    # CALCULAR A ROTA
    route_meter = nx.shortest_path_length(g, start_node, end_node, weight='length')
    route = nx.shortest_path(g, start_node, end_node, weight='length')

    return route_meter, route

#-----------------------------------------------
# FUNÇÃO QUANDO CLICAR EM ''CALCULAR''

def calc():
    clear_txt()

    #1º PASSO - PEGAR TODAS A COORDENADA DOS IMOVEIS DA AMOSTRA
    data_imoveis = get_coord_points('Avaliados', path_imoveis) #essa função retorna o dataframe

    #2º PASSO - PEGAR TODAS A COORDENADAS DE PONTOS VALORIZANTES:

    if var_rb.get() == '1':
        print('1')
        data_valorizantes_points = get_coord_points('Point_valuing', path_valorizante)

    #3º PASSO - ADICIONAR COLUNAS DAS DISTANCIAS MINIMAS - DISTANCIA EUCLIDIANA E ROTAS
        # SE O VALORIZANTE FOR PONTO
        x1 = data_imoveis['E']
        y1 = data_imoveis['N']
        x2 = data_valorizantes_points['E']
        y2 = data_valorizantes_points['N']

        global fig_list, fig_list_names
        fig_list = []
        fig_list_names = []
        for row_valuing,i in enumerate(data_valorizantes_points['ID_NAME']):

            #print(i)
            dist_min_list = []
            route_min_list = []

            for row_imovel in range((data_imoveis.shape[0])): #informa o numero de rows...se for 1 é o numero de colunas...se for shape apenas mostra tupla (rows, colunas)
                #print(row_imovel)
                dist_min_list.append(dist_min_point(x1[row_imovel],y1[row_imovel],x2[row_valuing],y2[row_valuing]))
                route_min = calc_min_routes_nx((x1[row_imovel],y1[row_imovel]),(x2[row_valuing],y2[row_valuing]))
                route_min_list.append(route_min[0]) #origem,destino em tuplas

                # GERAR E SALVAR IMAGENS PARA CADA ROTA
                fig, ax = ox.plot_graph_route(g, route_min[1])
                fig.savefig(f'{path_png}/ROUTE_{data_imoveis["ID_NAME"][row_imovel]}_{i}.PNG', dpi=100)
                fig_list.append(fig)  # salvei fig
                fig_list_names.append(f'ROUTE_{data_imoveis["ID_NAME"][row_imovel]}_{i}')  # salvei o nome da fig
                txt.insert(tkinter.END, f'Imóvel {data_imoveis["ID_NAME"][row_imovel]}...{i}\n')
                root.update()

            data_imoveis[f'Dist_{i}'] = dist_min_list
            data_imoveis[f'Route_{i}'] = route_min_list
            #---
        data_imoveis['VT'] = valores_totais
            #---
        data_imoveis.to_csv(f"{path_tabelas}/Dist_Routes_Imoveis_To_Points.csv")
        print(data_imoveis)

        #ENCONTRAR AS CORRELAÇÕES ENTRE VT E DISTS;ROUTES

        #print(data_imoveis.shape[1])
        correl_list = []
        n_col = data_imoveis.shape[1]
        txt.delete(1.0, tkinter.END)
        txt.insert(tkinter.END, f'Correlações de Pearson:\n\n')
        for colunm in range(data_imoveis.shape[1]):
            if colunm>2: #nao me interessa as 3 primeiras colunas
                x = data_imoveis.iloc[:, colunm]
                y = data_imoveis.iloc[:, n_col - 1]
                # print(x)
                # print(y)
                correl = pearsonr(x, y)[0]
                correl_list.append(correl)
                col_name_x = data_imoveis.columns[colunm]
                col_name_y = data_imoveis.columns[n_col - 1]
                txt.insert(tkinter.END, f'{col_name_x} x {col_name_y}:\n')
                txt.insert(tkinter.END, f'{round(correl,4)}\n\n')

    #===========================================================================================
    # SE O VALORIZANTE FOR LINHA
    if var_rb.get() == '0':
        print('SE FOR LINHA')
        data_valorizantes_lines =  get_coord_lines("Line_valuing", path_valorizante)
        print(data_valorizantes_lines) # é uma lista com dataframes, uma para cada polyline de referencia

        x_imoveis = data_imoveis['E']
        y_imoveis = data_imoveis['N']

        print(data_imoveis)
        dist_min_list = []
        route_min_list = []
        coord_min_list = []
        fig_list = []
        fig_list_names = []
        for data_valorizantes in data_valorizantes_lines:

            x_lines = data_valorizantes['E']
            y_lines = data_valorizantes['N']

            for row_imovel in range(data_imoveis.shape[0]):  # informa o numero de rows...se for 1 é o numero de colunas...se for shape apenas mostra tupla (rows, colunas)

                dist_min_temp = []
                coord_min_temp = []
                name_valuing = []

                for row_valuing, i in enumerate(data_valorizantes['ID_NAME']):

                    if row_valuing != data_valorizantes.shape[0]-1: #verificação para nao pegar a ultima linha...se nao fica sem par
                        x1, y1, x2, y2, xp, yp = x_lines[row_valuing], y_lines[row_valuing], x_lines[row_valuing+1], y_lines[row_valuing+1], x_imoveis[row_imovel], y_imoveis[row_imovel]
                        dist_min_p_r = dist_min_point_reta(x1, y1, x2, y2, xp, yp)[0]
                        coord_dist_min = (dist_min_point_reta(x1, y1, x2, y2, xp, yp)[1], dist_min_point_reta(x1, y1, x2, y2, xp, yp)[2])

                        dist_min_temp.append(dist_min_p_r)
                        coord_min_temp.append(coord_dist_min) #coordenadas referente ao ponto que produz menor dist euclidiana.
                        coord_min_temp.append((x1, y1))
                        coord_min_temp.append((x2, y2))

                coord_min_temp = set(coord_min_temp)

                dist_min_list.append(min(dist_min_temp)) #pegando a minima das minimas dist. euclidianas
                indice = dist_min_temp.index(min(dist_min_temp)) #pegando o indice dess menor dist. euclidiana
                #coord_min_list.append(coord_min_temp[indice])

                #CALCULAR ROTAS MINIMAS PARA CADA DIST. MIN. EUCLIDIANA DA POLYLINE e para cada x1 y1 x2 y2
                route_min_list_meter = []
                route_min_list_all = []

                for coord in coord_min_temp:
                    route_min = calc_min_routes_nx((xp, yp), coord)
                    route_min_list_meter.append(route_min[0])
                    route_min_list_all.append(route_min[1])
                    print(f'IMOVEL = {xp, yp}')
                    print(f'Coord: {coord}')
                    print(f'Dist: {route_min[0]}')

                route_min_meter = min(route_min_list_meter)
                indice = route_min_list_meter.index(min(route_min_list_meter))
                route_min_all = route_min_list_all[indice]

                #COM A COORDENADA EM MAOS...CALCULAR O ROUTE PARA ESSA COORDENADA

                #route_min = calc_min_routes(( xp, yp ), coord_min_temp[indice])
                name_valuing.append(i)
                #route_min_list.append(route_min_all)
                route_min_list.append(route_min_meter)

                #GERAR E SALVAR IMAGENS PARA CADA ROTA

                fig, ax = ox.plot_graph_route(g, route_min_all)
                fig.savefig(f'{path_png}/{data_imoveis["ID_NAME"][row_imovel]}_{i}.PNG',dpi=100)
                fig_list.append(fig) #salvei fig
                fig_list_names.append(f'ROUTE_{data_imoveis["ID_NAME"][row_imovel]}_{i}') #salvei o nome da fig
                txt.insert(tkinter.END, f'Imóvel {data_imoveis["ID_NAME"][row_imovel]}...{i}\n')
                root.update() #USAR UPDATE PARA MANTER O USUÁRIO ATUALIZADO SOBRE O PROCESSAMENTO


            print(dist_min_list)
            print(f'Dist_{name_valuing[0]}')
            data_imoveis[f'Dist_{name_valuing[0]}'] = dist_min_list
            data_imoveis[f'Route_{name_valuing[0]}'] = [ routes for routes in route_min_list  ]

            dist_min_list.clear()
            route_min_list.clear()
        data_imoveis['VT'] = valores_totais
        print(f'TESTE:\n{data_imoveis}')
        data_imoveis.to_csv(f"{path_tabelas}/Dist_Routes_Imoveis_To_Lines.csv")

        # ENCONTRAR AS CORRELAÇÕES ENTRE VT E DISTS;ROUTES
        correl_list = []
        n_col = data_imoveis.shape[1]
        txt.delete(1.0, tkinter.END)
        txt.insert(tkinter.END, f'Correlações de Pearson:\n\n')
        for colunm in range(data_imoveis.shape[1]):
            if colunm > 2:  # nao me interessa as 3 primeiras colunas
                x = data_imoveis.iloc[:, colunm]
                y = data_imoveis.iloc[:, n_col - 1]
                # print(x)
                # print(y)
                correl = pearsonr(x, y)[0]
                correl_list.append(correl)
                col_name_x = data_imoveis.columns[colunm] #PEGA NOME PELO INDEX
                col_name_y = data_imoveis.columns[n_col - 1]
                txt.insert(tkinter.END, f'{col_name_x} x {col_name_y}:\n')
                txt.insert(tkinter.END, f'{round(correl, 4)}\n\n')

    # NOMES PARA APARECER NO COMBOBOX
    name_combo['values'] = fig_list_names

    message_save()

# BOTAO DE CALCULO
button3 = tkinter.Button(root, text='CALCULAR', font=('ARIAL', 10), command=calc)
button3.place(anchor='nw',x=710, y=80)

#INTERFACE PARA INTERLIGACAO ENTRE MATPLOTLIB E TKINTER
global fig_list, fig_list_names, name_combo

#FUNÇÃO PARA MOSTRAR FIGURAS DAS ROTAS
def show_figs(*args):
    fig_name = name_combo.get()
    indice = fig_list_names.index(fig_name)

    fig = fig_list[indice]
    fig.set_figheight(4)
    fig.set_figwidth(4)
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=label_frame_fig)#label_frame_fig
    canvas.draw()
    canvas.get_tk_widget().place(anchor='center',x=250, y=232.5)

    toolbar = NavigationToolbar2Tk(canvas, master=label_frame_fig)#label_frame_fig
    toolbar.update()
    canvas.get_tk_widget().place(anchor='center',x=250, y=232.5)

# CRIANDO E CONFIGURANDO O COMBOBOX
name_str = tkinter.StringVar()
name_combo = ttk.Combobox(label_frame_fig, textvariable=name_str, width=30)
name_combo['state'] = 'readonly'
name_combo.place(anchor='nw',x=150, y=0)

name_combo.bind('<<ComboboxSelected>>',show_figs) #vincular uma função ao evento de selecionar algum nome do combobox https://www.pythontutorial.net/tkinter/tkinter-combobox/

# RESULTADOS RESUMO
clear_txt()

root.mainloop()
