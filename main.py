import streamlit as st
import requests
import json
import random
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from google.generativeai import configure, GenerativeModel

# Configuração das chaves de API
MY_SHIP_TRACKING_API_KEY = os.environ.get("MY_SHIP_TRACKING_API_KEY", "SUA_CHAVE_API_MYSHIPTRACKING")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "SUA_CHAVE_API_GEMINI")

# Configurar a API do Google Gemini
configure(api_key=GOOGLE_API_KEY)
gemini_model = GenerativeModel('gemini-pro')

class ShippingAnalyzer:
    def __init__(self, myship_api_key, gemini_model):
        """Inicializa o analisador de tráfego marítimo."""
        self.myship_api_key = myship_api_key
        self.base_url = "https://api.myshiptracking.com/v1"
        self.gemini_model = gemini_model
        
    def get_ships_near_port(self, port_name):
        """Obtém navios próximos a um porto específico."""
        # Primeiro, buscar o porto pelo nome
        port_endpoint = f"{self.base_url}/ports"
        
        port_params = {
            "api_key": self.myship_api_key,
            "name": port_name
        }
        
        port_response = requests.get(port_endpoint, params=port_params)
        
        if port_response.status_code != 200:
            return {"error": f"Failed to fetch port data: {port_response.status_code}"}
        
        port_data = port_response.json()
        
        if not port_data or len(port_data) == 0:
            return {"error": f"No ports found with name: {port_name}"}
        
        # Usar o primeiro porto encontrado
        port = port_data[0]
        
        # Agora buscar navios ativos que têm este porto como destino ou origem
        vessels_endpoint = f"{self.base_url}/vessels"
        
        vessels_params = {
            "api_key": self.myship_api_key,
            "name": ""  # Busca ampla
        }
        
        vessels_response = requests.get(vessels_endpoint, params=vessels_params)
        
        if vessels_response.status_code != 200:
            return {"error": f"Failed to fetch vessels data: {vessels_response.status_code}"}
        
        all_vessels = vessels_response.json()
        
        # Filtrar apenas navios relacionados ao porto
        port_related_vessels = []
        
        for vessel in all_vessels:
            if vessel.get("destination") == port_name or vessel.get("last_port") == port_name:
                port_related_vessels.append(vessel)
        
        return {"ships": port_related_vessels}
        
    def get_ships_in_area(self, latitude, longitude, radius=50):
        """Obtém navios em uma área específica (dados simulados)."""
        # Dados simulados para demonstração
        ship_types = ["Cargo", "Tanker", "Passenger", "Fishing", "Tug", "Pleasure Craft"]
        ship_flags = ["Panama", "Liberia", "Marshall Islands", "Singapore", "Malta", "Bahamas"]
        ports = ["Rotterdam", "Singapore", "Shanghai", "Antwerp", "Hamburg", "Los Angeles"]
        statuses = ["Underway using engine", "At anchor", "Moored", "Stopped", "Restricted maneuverability"]
        
        # Gerar entre 5 e 15 navios aleatórios
        num_ships = random.randint(5, 15)
        ships = []
        
        for i in range(num_ships):
            # Gera dados aleatórios para cada navio
            ship = {
                "mmsi": str(random.randint(100000000, 999999999)),
                "name": f"VESSEL {random.randint(1000, 9999)}",
                "type": random.choice(ship_types),
                "speed": round(random.uniform(0, 20), 1),
                "course": round(random.uniform(0, 359), 1),
                "latitude": latitude + (random.random() - 0.5) * (radius/50),
                "longitude": longitude + (random.random() - 0.5) * (radius/50),
                "flag": random.choice(ship_flags),
                "destination": random.choice(ports),
                "status": random.choice(statuses)
            }
            ships.append(ship)
        
        return {
            "ships": ships, 
            "note": "Dados simulados para demonstração. API MyShipTracking não suporta busca por área geográfica."
        }
    
    def _get_region_coordinates(self, region_name, custom_coords=None):
        """Obtém coordenadas de uma região conhecida ou customizada."""
        if custom_coords:
            return custom_coords
        
        # Coordenadas pré-definidas para regiões comuns
        regions = {
            "Canal de Suez": {"lat": 30.4276, "lon": 32.3439, "radius": 80},
            "Estreito de Gibraltar": {"lat": 35.9897, "lon": -5.6125, "radius": 50},
            "Canal do Panamá": {"lat": 9.1480, "lon": -79.8308, "radius": 70},
            "Estreito de Malaca": {"lat": 1.7136, "lon": 101.4661, "radius": 100},
            "Porto de Roterdã": {"lat": 51.9244, "lon": 4.4777, "radius": 40},
            "Costa do Brasil": {"lat": -23.9619, "lon": -46.3042, "radius": 120},
            "Porto de Los Angeles": {"lat": 33.7283, "lon": -118.2712, "radius": 50},
            "Porto de Shanghai": {"lat": 31.2304, "lon": 121.4737, "radius": 60}
        }
        
        return regions.get(region_name, {"lat": 0, "lon": 0, "radius": 50})
    
    def analyze_region_traffic(self, region_name, custom_coords=None):
        """Analisa o tráfego marítimo em uma região específica."""
        # Determinar coordenadas com base na região
        coords = self._get_region_coordinates(region_name, custom_coords)
        
        # Obter dados dos navios
        ships_data = self.get_ships_in_area(coords["lat"], coords["lon"], coords.get("radius", 50))
        
        if "error" in ships_data:
            return {"error": ships_data["error"]}
            
        # Extrair dados dos navios para análise
        ships = ships_data.get("ships", [])
        
        # Processar e agregar dados
        analysis_data = self._process_ships_data(ships, region_name)
        
        # Realizar análise com IA
        analysis_results = self._analyze_with_ai(analysis_data)
        
        # Resultados completos
        result = {
            "raw_data": ships_data,
            "analysis_data": analysis_data,
            "analysis_text": analysis_results,
            "note": ships_data.get("note", "")
        }
        
        return result
    
    def _process_ships_data(self, ships, region_name):
        """Processa dados brutos de navios para análise."""
        total_ships = len(ships)
        
        # Contagem de tipos de navios
        ship_types = {}
        for ship in ships:
            ship_type = ship.get("type", "Desconhecido")
            ship_types[ship_type] = ship_types.get(ship_type, 0) + 1
        
        # Velocidade média
        speeds = [ship.get("speed", 0) for ship in ships if ship.get("speed") is not None]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        
        # Status dos navios
        statuses = {}
        for ship in ships:
            status = ship.get("status", "Desconhecido")
            statuses[status] = statuses.get(status, 0) + 1
        
        # Bandeiras
        flags = {}
        for ship in ships:
            flag = ship.get("flag", "Desconhecido")
            flags[flag] = flags.get(flag, 0) + 1
        
        # Direções (com base no curso)
        directions = {
            "Norte": 0, "Nordeste": 0, "Leste": 0, "Sudeste": 0,
            "Sul": 0, "Sudoeste": 0, "Oeste": 0, "Noroeste": 0
        }
        
        for ship in ships:
            course = ship.get("course")
            if course is not None:
                if 337.5 <= course or course < 22.5:
                    directions["Norte"] += 1
                elif 22.5 <= course < 67.5:
                    directions["Nordeste"] += 1
                elif 67.5 <= course < 112.5:
                    directions["Leste"] += 1
                elif 112.5 <= course < 157.5:
                    directions["Sudeste"] += 1
                elif 157.5 <= course < 202.5:
                    directions["Sul"] += 1
                elif 202.5 <= course < 247.5:
                    directions["Sudoeste"] += 1
                elif 247.5 <= course < 292.5:
                    directions["Oeste"] += 1
                elif 292.5 <= course < 337.5:
                    directions["Noroeste"] += 1
        
        # Formatar dados agregados para análise
        analysis_data = {
            "region": region_name,
            "total_ships": total_ships,
            "ship_types": ship_types,
            "avg_speed": round(avg_speed, 1),
            "statuses": statuses,
            "flags": flags,
            "directions": directions,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return analysis_data
    
    def _analyze_with_ai(self, analysis_data):
        """Utiliza o modelo Gemini para analisar os dados de tráfego marítimo."""
        # Formatar dados como texto para o modelo
        prompt_text = f"""
        Análise de tráfego marítimo na região: {analysis_data['region']}
        Dados coletados em tempo real:
        - Total de navios na área: {analysis_data['total_ships']}
        - Velocidade média: {analysis_data['avg_speed']} nós
        - Tipos de navios: {json.dumps(analysis_data['ship_types'])}
        - Status dos navios: {json.dumps(analysis_data['statuses'])}
        - Bandeiras: {json.dumps(analysis_data['flags'])}
        - Direções: {json.dumps(analysis_data['directions'])}
        
        Com base nesses dados, faça uma análise completa do tráfego marítimo atual nesta região.
        Inclua insights sobre:
        1. Fluxo e densidade do tráfego
        2. Possíveis congestionamentos ou áreas de preocupação
        3. Distribuição e tipos de embarcações
        4. Padrões de movimento (direções predominantes)
        5. Recomendações para navegação segura na região
        
        Formatado como um relatório profissional para operadores marítimos.
        """
        
        # Fazer a consulta ao modelo Gemini
        try:
            response = self.gemini_model.generate_content(prompt_text)
            analysis_text = response.text
        except Exception as e:
            analysis_text = f"Erro ao gerar análise: {str(e)}\n\nDados disponíveis para análise manual:\n{json.dumps(analysis_data, indent=2)}"
        
        return analysis_text

def create_app():
    """Cria a aplicação Streamlit."""
    st.set_page_config(page_title="Análise de Tráfego Marítimo", page_icon="🚢", layout="wide")
    
    st.title("🚢 Análise de Tráfego Marítimo em Tempo Real")
    st.write("Esta aplicação utiliza dados AIS em tempo real e IA para analisar o tráfego marítimo em regiões importantes ao redor do mundo.")
    
    # Inicializar o analisador
    analyzer = ShippingAnalyzer(MY_SHIP_TRACKING_API_KEY, gemini_model)
    
    # Layout em duas colunas
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Região de Interesse")
        
        # Opção de selecionar região pré-definida ou coordenadas customizadas
        search_option = st.radio("Método de busca:", ["Região pré-definida", "Coordenadas específicas"])
        
        if search_option == "Região pré-definida":
            # Lista de regiões pré-definidas
            regions = [
                "Canal de Suez",
                "Estreito de Gibraltar",
                "Canal do Panamá",
                "Estreito de Malaca",
                "Porto de Roterdã",
                "Costa do Brasil",
                "Porto de Los Angeles",
                "Porto de Shanghai"
            ]
            region = st.selectbox("Selecione a região:", regions)
            custom_coords = None
        else:
            # Entrada de coordenadas customizadas
            st.write("Insira as coordenadas da área de interesse:")
            lat = st.number_input("Latitude:", value=0.0, min_value=-90.0, max_value=90.0, step=0.1)
            lon = st.number_input("Longitude:", value=0.0, min_value=-180.0, max_value=180.0, step=0.1)
            radius = st.slider("Raio (milhas náuticas):", min_value=10, max_value=200, value=50, step=10)
            region = f"Coordenadas Personalizadas ({lat}, {lon})"
            custom_coords = {"lat": lat, "lon": lon, "radius": radius}
        
        # Botão para realizar análise
        if st.button("Analisar Tráfego"):
            with st.spinner("Obtendo dados de navios e realizando análise..."):
                result = analyzer.analyze_region_traffic(region, custom_coords if search_option == "Coordenadas específicas" else None)
                
                if "error" in result:
                    st.error(f"Erro ao obter dados: {result['error']}")
                else:
                    st.session_state.analysis_result = result
                    st.success("Análise concluída!")
                    
                    # Mostrar nota sobre dados simulados, se aplicável
                    if "note" in result:
                        st.warning(result["note"])
    
    with col2:
        if "analysis_result" in st.session_state:
            result = st.session_state.analysis_result
            
            st.subheader(f"Análise de Tráfego: {result['analysis_data']['region']}")
            
            # Layout em abas para organizar as informações
            tab1, tab2, tab3 = st.tabs(["Análise de IA", "Visualizações", "Dados Brutos"])
            
            with tab1:
                st.markdown(result["analysis_text"])
                
                # Mostrar timestamp da análise
                st.caption(f"Análise gerada em: {result['analysis_data']['timestamp']}")
            
            with tab2:
                # Visualizações dos dados
                st.subheader("Visualizações")
                
                # Dados analisados
                analysis_data = result["analysis_data"]
                
                # Layout para visualizações
                viz_col1, viz_col2 = st.columns(2)
                
                with viz_col1:
                    # Gráfico de pizza para tipos de navios
                    fig_types = px.pie(
                        names=list(analysis_data["ship_types"].keys()),
                        values=list(analysis_data["ship_types"].values()),
                        title="Distribuição por Tipo de Navio"
                    )
                    st.plotly_chart(fig_types, use_container_width=True)
                    
                    # Gráfico de barras para direções
                    fig_directions = px.bar(
                        x=list(analysis_data["directions"].keys()),
                        y=list(analysis_data["directions"].values()),
                        title="Distribuição por Direção"
                    )
                    st.plotly_chart(fig_directions, use_container_width=True)
                
                with viz_col2:
                    # Gráfico de barras para status dos navios
                    fig_status = px.bar(
                        x=list(analysis_data["statuses"].keys()),
                        y=list(analysis_data["statuses"].values()),
                        title="Status dos Navios"
                    )
                    st.plotly_chart(fig_status, use_container_width=True)
                    
                    # Gráfico de pizza para bandeiras
                    fig_flags = px.pie(
                        names=list(analysis_data["flags"].keys()),
                        values=list(analysis_data["flags"].values()),
                        title="Distribuição por Bandeira"
                    )
                    st.plotly_chart(fig_flags, use_container_width=True)
                
                # Visualização em mapa
                st.subheader("Mapa de Navios")
                
                # Dados dos navios
                ships = result["raw_data"].get("ships", [])
                
                if ships:
                    # Criar DataFrame para o mapa
                    map_data = pd.DataFrame([
                        {
                            "lat": ship.get("latitude"),
                            "lon": ship.get("longitude"),
                            "name": ship.get("name", "Unknown"),
                            "type": ship.get("type", "Unknown"),
                            "speed": ship.get("speed", 0),
                            "course": ship.get("course", 0),
                            "flag": ship.get("flag", "Unknown"),
                            "destination": ship.get("destination", "Unknown"),
                            "status": ship.get("status", "Unknown")
                        }
                        for ship in ships if ship.get("latitude") and ship.get("longitude")
                    ])
                    
                    # Criar mapa
                    fig_map = px.scatter_mapbox(
                        map_data,
                        lat="lat",
                        lon="lon",
                        hover_name="name",
                        hover_data=["type", "speed", "course", "flag", "destination", "status"],
                        color="type",
                        zoom=6,
                        height=500
                    )
                    
                    fig_map.update_layout(
                        mapbox_style="open-street-map",
                        mapbox_zoom=7,
                        mapbox_center={"lat": analysis_data["region"]["lat"] if isinstance(analysis_data["region"], dict) else 0, 
                                       "lon": analysis_data["region"]["lon"] if isinstance(analysis_data["region"], dict) else 0},
                        margin={"r":0,"t":0,"l":0,"b":0}
                    )
                    
                    st.plotly_chart(fig_map, use_container_width=True)
                else:
                    st.warning("Não há dados de navios disponíveis para mostrar no mapa.")
            
            with tab3:
                # Dados brutos
                st.subheader("Dados Brutos")
                
                ships = result["raw_data"].get("ships", [])
                
                if ships:
                    # Converter para DataFrame para melhor visualização
                    df = pd.DataFrame(ships)
                    st.dataframe(df)
                    
                    # Opção para download dos dados
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "Download CSV",
                        csv,
                        f"ships_data_{analysis_data['region'].replace(' ', '_').lower()}_{analysis_data['timestamp'].replace(':', '-').replace(' ', '_')}.csv",
                        "text/csv",
                        key="download-csv"
                    )
                else:
                    st.warning("Não há dados brutos disponíveis.")
        else:
            st.info("Selecione uma região e clique em 'Analisar Tráfego' para ver os resultados.")
    
    # Rodapé
    st.markdown("---")
    st.caption("Desenvolvido como prova de conceito para análise de tráfego marítimo utilizando dados AIS e IA generativa.")

if __name__ == "__main__":
    create_app()
