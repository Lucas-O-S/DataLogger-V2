import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
from datetime import datetime
import pytz
 
# Constants for IP and port
IP_ADDRESS = "4.228.64.5"
PORT_STH = 8666
DASH_HOST = "0.0.0.0"  # Set this to "0.0.0.0" to allow access from any IP
lamp = "05x"
 
# Function to get data from the API
def get_data(lastN,dataType):
    url = f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/Lamp/id/urn:ngsi-ld:Lamp:{lamp}/attributes/{dataType}?lastN={lastN}"
    headers = {
        'fiware-service': 'smart',
        'fiware-servicepath': '/'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        try:
            values = data['contextResponses'][0]['contextElement']['attributes'][0]['values']
            return values
        except KeyError as e:
            print(f"Key error: {e}")
            return []
    else:
        print(f"Error accessing {url}: {response.status_code}")
        return []

 
# Function to convert UTC timestamps to São Paulo time
def convert_to_sao_paulo_time(timestamps):
    utc = pytz.utc
    lisbon = pytz.timezone('America/Sao_Paulo')
    converted_timestamps = []
    for timestamp in timestamps:
        try:
            timestamp = timestamp.replace('T', ' ').replace('Z', '')
            converted_time = utc.localize(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')).astimezone(lisbon)
        except ValueError:
            # Handle case where milliseconds are not present
            converted_time = utc.localize(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')).astimezone(lisbon)
        converted_timestamps.append(converted_time)
    return converted_timestamps
 
# Set lastN value
lastN = 10  # Get 10 most recent points at each interval
 
app = dash.Dash(__name__)
 
app.layout = html.Div([
    html.H1('ESP 32 Data Viewer'),
    dcc.Graph(id='general-graph'),

    dcc.Graph(id='luminosity-graph'),
    dcc.Graph(id='temperature-graph'),
    dcc.Graph(id='humidity-graph'),

    # Store to hold historical data
    dcc.Store(id='luminosity-data-store', data={'timestamps': [], 'luminosity_values': []}),
    dcc.Store(id='temperature-data-store', data={'timestamps': [], 'temperature_values': []}),
    dcc.Store(id='humidity-data-store', data={'timestamps': [], 'humidity': []}),

    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # in milliseconds (10 seconds)
        n_intervals=0
    )
    
    
])

@app.callback(
    Output('luminosity-data-store', 'data'),
    Output('temperature-data-store', 'data'),
    Input('interval-component', 'n_intervals'),
    State('luminosity-data-store', 'data'),
    State('temperature-data-store', 'data')

)
def update_data_store(n, luminosity_data, temperature_data):
    luminosity_data = generic_update_data_store(n,luminosity_data,"luminosity")
    temperature_data = generic_update_data_store(n,temperature_data,"temperature")

    return luminosity_data, temperature_data

@app.callback(
    Output('luminosity-graph', 'figure'),
    Input('luminosity-data-store', 'data')
)
def update_graph(stored_data):
    fig_luminosity = generic_update_graph(stored_data,"luminosity","Luminosidade","orange")
    return fig_luminosity


@app.callback(
    Output('temperature-graph', 'figure'),
    Input('temperature-data-store', 'data')
)
def update_graph(stored_data):
    fig_temperature = generic_update_graph(stored_data,"temperature","Temperatura","red")
    return fig_temperature


def generic_update_data_store(n, stored_data,dataType):
    # Get luminosity data
    data = get_data(lastN, dataType)

    if data:
        # Extract values and timestamps
        data_values = [float(entry['attrValue']) for entry in data]  # Ensure values are floats
        timestamps = [entry['recvTime'] for entry in data]

        # Calculate the average luminosity for the current interval
        average_data = sum(data_values) / len(data_values)

        # Convert timestamps to Lisbon time
        timestamps = convert_to_sao_paulo_time(timestamps)

        # Append the new average and the latest timestamp to stored data
        stored_data['timestamps'].append(timestamps[-1])  # Store only the latest timestamp
        stored_data[f'{dataType}_values'].append(average_data)  # Store the average luminosity

        # Calculate total average luminosity
        total_data = sum(stored_data[f'{dataType}_values'])
        total_count = len(stored_data[f'{dataType}_values'])
        stored_data[f'total_average_{dataType}'] = total_data / total_count if total_count > 0 else 0

        return stored_data
    return stored_data

def generic_update_graph(stored_data, data_type,name, data_color):
    if stored_data['timestamps'] and stored_data[f'{data_type}_values']:
        # Create traces for the plot
        trace_average = go.Scatter(
            x=stored_data['timestamps'],
            y=stored_data[f'{data_type}_values'],
            mode='lines+markers',
            name=f'{name}',
            line=dict(color=data_color)
        )

        # Create a trace for the total average
        total_average = stored_data[f'total_average_{data_type}']
        trace_total_average = go.Scatter(
            x=[stored_data['timestamps'][0], stored_data['timestamps'][-1]],
            y=[total_average, total_average],
            mode='lines',
            name=f'Media da {name}',
            line=dict(color='blue', dash='dash')
        )

        # Create figure
        fig_data = go.Figure(data=[trace_average, trace_total_average])

        # Update layout
        fig_data.update_layout(
            title=f'{name}',
            xaxis_title='Timestamp',
            yaxis_title=f'{data_type}',
            hovermode='closest'
        )

        return fig_data

    return {} 
if __name__ == '__main__':
    app.run_server(debug=True, host=DASH_HOST, port=8050)
    

