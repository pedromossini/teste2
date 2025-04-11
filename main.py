import requests
import json
import os
from google.generativeai import configure, GenerativeModel
import streamlit as st

# Configuração das chaves de API
import os
MY_SHIP_TRACKING_API_KEY = os.environ.get("MY_SHIP_TRACKING_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Configurar a API do Gemini
configure(api_key=GOOGLE_API_KEY)
model = GenerativeModel('gemini-pro')

class ShippingAnalyzer:
    def __init__(self, myship_api_key, gemini_model):
        self.myship_api_key = myship_api_key
        self.gemini_model = gemini_model
        self.base_url = "https://api.myshiptracking.com/v1"
        
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
    
    # Infelizmente, não há um parâmetro direto para buscar por porto
    # Precisamos fazer uma busca ampla e filtrar depois
    vessels_params = {
        "api_key": self.myship_api_key,
        # Podemos usar uma string genérica para obter mais resultados
        "name": ""  # Busca ampla
    }
    
    vessels_response = requests.get(vessels_endpoint, params=vessels_params)
    
    if vessels_response.status_code != 200:
        return {"error": f"Failed to fetch vessels data: {vessels_response.status_code}"}
    
    all_vessels = vessels_response.json()
    
    # Filtrar apenas navios relacionados ao porto
    # Nota: Esta é uma simplificação, pois a API não fornece diretamente esta funcionalidade
    port_related_vessels = []
    
    for vessel in all_vessels:
        if vessel.get("destination") == port_name or vessel.get("last_port") == port_name:
            port_related_vessels.append(vessel)
    
    return {"ships": port_related_vessels}
    
    def get_port_info(self, port_name):
        """Obtém informações sobre um porto específico."""
        endpoint = f"{self.base_url}/ports/search"
        
        params = {
            "api_key": self.myship_api_key,
            "query": port_name
        }
        
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch port data: {response.status_code}"}
    
    def analyze_region_traffic(self, region_name, custom_coords=None):
        """Analisa o tráfego marítimo em uma região específica ou em coordenadas personalizadas."""
        # Mapeamento de regiões para coordenadas
        region_coordinates = {
            "canal de suez": {"lat": 30.4276, "lon": 32.3439, "radius": 80},
            "estreito de malaca": {"lat": 1.7691, "lon": 101.0608, "radius": 100},
            "canal do panamá": {"lat": 9.0800, "lon": -79.6800, "radius": 70},
            "porto de santos": {"lat": -23.9619, "lon": -46.3042, "radius": 40},
            "porto de singapura": {"lat": 1.2903, "lon": 103.8521, "radius": 40},
            "porto de roterdã": {"lat": 51.9244, "lon": 4.4777, "radius": 40},
            "estreito de gibraltar": {"lat": 36.0000, "lon": -5.6000, "radius": 50},
            "baía de guanabara": {"lat": -22.8350, "lon": -43.2931, "radius": 30}
        }
        
        # Se foram fornecidas coordenadas personalizadas, use-as
        if custom_coords:
            coords = custom_coords
            location_source = "coordenadas fornecidas pelo usuário"
        else:
            # Caso contrário, verifique se é uma região conhecida
            region_lower = region_name.lower()
            if region_lower in region_coordinates:
                coords = region_coordinates[region_lower]
                location_source = "base de dados predefinida"
            else:
                # Se não for uma região conhecida, retorne uma mensagem informativa
                return {
                    "region": region_name,
                    "data": "Região não encontrada na base de dados",
                    "analysis": "Esta região não está em nossa base de dados. Por favor, forneça coordenadas específicas (latitude e longitude) ou escolha uma das regiões predefinidas."
                }
        
        # Agora que temos as coordenadas, vamos buscar os dados dos navios
        ships_data = self.get_ships_in_area(coords["lat"], coords["lon"], coords.get("radius", 50))
        
        # Preparar dados para análise com Gemini
        if "error" not in ships_data:
            ships_count = len(ships_data.get("ships", []))
            
            # Coletar tipos de navios e velocidades
            ship_types = {}
            avg_speed = 0
            stopped_ships = 0
            
            for ship in ships_data.get("ships", []):
                ship_type = ship.get("type", "Unknown")
                speed = ship.get("speed", 0)
                
                if ship_type in ship_types:
                    ship_types[ship_type] += 1
                else:
                    ship_types[ship_type] = 1
                
                avg_speed += speed
                
                if speed < 1:  # navio considerado parado
                    stopped_ships += 1
            
            if ships_count > 0:
                avg_speed = avg_speed / ships_count
            
            # Criar prompt para o Gemini
            prompt = f"""
            Análise de tráfego marítimo na região: {region_name}
            Localização obtida por: {location_source}
            Coordenadas: Latitude {coords["lat"]}, Longitude {coords["lon"]}
            Raio de análise: {coords.get("radius", 50)} milhas náuticas
            
            Dados coletados em tempo real:
            - Total de navios na área: {ships_count}
            - Navios parados ou com velocidade muito baixa: {stopped_ships}
            - Velocidade média dos navios: {avg_speed:.2f} nós
            - Tipos de navios presentes: {json.dumps(ship_types)}
            
            Com base nesses dados:
            1. Faça uma análise detalhada do tráfego marítimo atual nesta região.
            2. Indique se há congestionamento e qual o nível de tráfego (baixo, médio, alto).
            3. Avalie se seria recomendável utilizar esta rota neste momento.
            4. Identifique possíveis problemas ou gargalos na região.
            5. Sugira rotas alternativas se o congestionamento for significativo.
            """
            
            # Obter análise do Gemini
            response = self.gemini_model.generate_content(prompt)
            return {
                "region": region_name,
                "coordinates": coords,
                "data": {
                    "ships_count": ships_count,
                    "stopped_ships": stopped_ships,
                    "avg_speed": f"{avg_speed:.2f}",
                    "ship_types": ship_types
                },
                "analysis": response.text
            }
        else:
            return {
                "region": region_name,
                "coordinates": coords,
                "data": f"Erro ao obter dados de navios: {ships_data.get('error', 'Erro desconhecido')}",
                "analysis": "Não foi possível obter dados de tráfego marítimo para esta região no momento."
            }

# Interface Streamlit para uso fácil
def create_app():
    st.title("Análise de Tráfego Marítimo")
    
    analyzer = ShippingAnalyzer(MY_SHIP_TRACKING_API_KEY, model)
    
    # Opções de pesquisa
    search_option = st.radio(
        "Como deseja buscar a região?",
        ("Regiões pré-definidas", "Nome da região", "Coordenadas específicas")
    )
    
    if search_option == "Regiões pré-definidas":
        predefined_regions = [
            "Canal de Suez", 
            "Estreito de Malaca", 
            "Canal do Panamá", 
            "Porto de Santos", 
            "Porto de Singapura", 
            "Porto de Roterdã",
            "Estreito de Gibraltar",
            "Baía de Guanabara"
        ]
        region = st.selectbox("Selecione a região:", predefined_regions)
        custom_coords = None
        
    elif search_option == "Nome da região":
        region = st.text_input("Digite o nome da região marítima:")
        custom_coords = None
        
    else:  # Coordenadas específicas
        region = st.text_input("Nome da região ou área (para referência):")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            latitude = st.number_input("Latitude:", value=0.0, format="%.6f")
        with col2:
            longitude = st.number_input("Longitude:", value=0.0, format="%.6f")
        with col3:
            radius = st.number_input("Raio (milhas náuticas):", value=50, min_value=1, max_value=500)
            
        custom_coords = {"lat": latitude, "lon": longitude, "radius": radius}
    
    if st.button("Analisar Tráfego"):
        if region or (search_option == "Coordenadas específicas" and custom_coords):
            with st.spinner("Obtendo dados e analisando..."):
                result = analyzer.analyze_region_traffic(region, custom_coords if search_option == "Coordenadas específicas" else None)
                
                st.subheader(f"Análise de Tráfego: {result['region']}")
                
                # Mostrar coordenadas usadas
                if "coordinates" in result:
                    st.write(f"**Coordenadas utilizadas:** Lat {result['coordinates']['lat']}, Lon {result['coordinates']['lon']}")
                    st.write(f"**Raio de análise:** {result['coordinates'].get('radius', 50)} milhas náuticas")
                
                # Exibir dados brutos se disponíveis
                if isinstance(result['data'], dict) and 'ships_count' in result['data']:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total de Navios", result['data']['ships_count'])
                    col2.metric("Navios Parados", result['data']['stopped_ships'])
                    col3.metric("Velocidade Média (nós)", result['data']['avg_speed'])
                    
                    # Mostrar tipos de navios
                    st.subheader("Tipos de Navios na Área")
                    
                    # Transformar os tipos de navios em um formato melhor para exibição
                    if result['data']['ship_types']:
                        ship_chart_data = {
                            "type": "pie",
                            "title": {"text": "Distribuição de Tipos de Navios"},
                            "series": [
                                {"name": tipo, "data": quantidade}
                                for tipo, quantidade in result['data']['ship_types'].items()
                            ]
                        }
                        st.json(ship_chart_data)  # Para visualização, na versão real isso seria um gráfico
                else:
                    st.warning(result['data'])
                
                # Exibir análise do Gemini
                st.subheader("Análise de Tráfego")
                st.write(result['analysis'])
        else:
            st.error("Por favor, forneça informações sobre a região para análise.")

    # Adicionar informação sobre regiões disponíveis
    with st.expander("Regiões marítimas disponíveis na base de dados"):
        st.write("""
        - Canal de Suez
        - Estreito de Malaca
        - Canal do Panamá
        - Porto de Santos
        - Porto de Singapura
        - Porto de Roterdã
        - Estreito de Gibraltar
        - Baía de Guanabara
        
        Para outras regiões, utilize a opção de coordenadas específicas.
        """)

if __name__ == "__main__":
    create_app()
