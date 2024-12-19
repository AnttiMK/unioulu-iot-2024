const { InfluxDB } = require('@influxdata/influxdb-client');

const url = 'https://influxdb-test-rahti2.2.rahtiapp.fi/';
const token = process.env.INFLUX_TOKEN;
const org = 'Iot2024';
const bucket = 'sensor-data';

const influxDB = new InfluxDB({ url, token });
const queryApi = influxDB.getQueryApi(org);

const query = `
from(bucket: "${bucket}")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r._field == "value")
`;

const dataStore = { latestData: null };

async function queryAndUpdateData() {
  setInterval(async () => {
    try {
      let latestData = null;
      let latestTimestamp = null;
      
      await new Promise((resolve, reject) => {
        queryApi.queryRows(query, {
          next(row, tableMeta) {
            const parsed = tableMeta.toObject(row);
            const record = {
              humidity: parseFloat(parsed._value) || 0.0,
              temperature: parseFloat(parsed.temperature) || 0.0,
              pressure: parseFloat(parsed.pressure) || 0.0,
              time: new Date(parsed._time),
            };

            if (!latestTimestamp || record.time > latestTimestamp) {
              latestData = record;
              latestTimestamp = record.time;
            }
          },
          error(err) {
            console.error('Query Error:', err);
            reject(err);
          },
          complete() {
            resolve();
          },
        });
      });

      if (latestData) {
        dataStore.latestData = latestData;
      }
    } catch (error) {
      console.error('Error during data query:', error);
    }
  }, 500);
}

queryAndUpdateData();

module.exports = dataStore;
