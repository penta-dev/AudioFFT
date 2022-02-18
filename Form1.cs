using Microsoft.VisualBasic.FileIO;
using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Diagnostics;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.IO;
using System.Windows.Forms;
using OfficeOpenXml;
using OfficeOpenXml.Drawing.Chart;

namespace SilabsCP2615
{
    public partial class Form1 : Form
    {
        string wavFile = "";
        string rootPath = "";
        string pythonAppsPath = "";
        string pythonPath = "";
        string inputPath = "";
        string outputPath = "";

        public Form1()
        {
            InitializeComponent();

            rootPath = AppDomain.CurrentDomain.BaseDirectory + @"..\..\";
            pythonAppsPath = rootPath + @"\PythonApps";
            pythonPath = AddQuotesIfRequired(GetPythonPath());
            outputPath = rootPath + @"\output";
            inputPath = rootPath + @"\input";
            wavFile = inputPath + @"\1000Hz_10s.wav";
            textBox2.Text = wavFile;
        }

        ///////////////////////////////////////////////
        /// Python THD 
        /// ///////////////////////////////////////////
        private void PythonTHD_Click(object sender, EventArgs e)
        {
            // Run THD calculator
            Process process = new Process();
            StringBuilder stdout = new StringBuilder();
            StringBuilder stderr = new StringBuilder();
            int timeout = 20 * 1000;
            try
            {
                process.StartInfo.FileName = pythonPath;
                process.StartInfo.Arguments = pythonAppsPath + @"\audiotools.py THD DVT " + wavFile;
                Log("PythonTHD: Calling: " + process.StartInfo.FileName + " " + process.StartInfo.Arguments);
                process.StartInfo.RedirectStandardError = true;
                process.StartInfo.RedirectStandardOutput = true;
                process.StartInfo.WindowStyle = ProcessWindowStyle.Hidden;
                process.StartInfo.CreateNoWindow = true;
                process.StartInfo.UseShellExecute = false;
                process.EnableRaisingEvents = false;
                process.OutputDataReceived += (sender2, eventArgs) => stdout.AppendLine(eventArgs.Data);
                process.ErrorDataReceived += (sender2, eventArgs) => stderr.AppendLine(eventArgs.Data);
                process.Start();
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();

                var processExited = process.WaitForExit(timeout);
                if (processExited == false)
                {
                    process.Kill();
                    Log("AudioTools::THD: Process exceeded timeout(" + timeout + "ms)");
                }
                else if (process.ExitCode != 0)
                {
                    Log("AudioTools::THD: Process failed to run with error: " + stderr.ToString());
                }
            }
            catch (Exception ex)
            {
                Log("AudioTools::THD: Failed to run with: " + ex);
                return;
            }
            process.Close();

            var result = new AcousticMeasurement();
            
            // Parse output
            var output = stdout.ToString();
            string[] substrings = output.Split(' ');
            for (int i = 0; i < (substrings.Length - 1); i++)
            {
                try
                {
                    if (substrings[i].Contains("Frequency:"))
                        result.THDMeasuredFrequency = ParsedoubleString(substrings[i + 1]);
                    else if (substrings[i].Contains("SPL:"))
                        result.THDMeasuredDbFS = ParsedoubleString(substrings[i + 1]);
                    else if (substrings[i].Contains("THDpercent:"))
                        result.THDMeasuredPercent = ParsedoubleString(substrings[i + 1]);
                }
                catch (Exception ex)
                {
                    Console.WriteLine(output);
                    Log("THD: Failed to parse: " + substrings[i] + " with: " + ex);
                    return;
                }
            }
            Log("THD: Freq[" + result.THDMeasuredFrequency.ToString("0.00") + "Hz] THD [" + result.THDMeasuredPercent.ToString("0.00") + "%, " + result.THDMeasuredDbFS.ToString("0.00") + "dBFs]");
            return;
        }


        ///////////////////////////////////////////////
        /// Python FFT 
        /// ///////////////////////////////////////////
        private void PythonFFT_Click(object sender, EventArgs e)
        {
            // Run FFT calculator
            Process process = new Process();
            StringBuilder stdout = new StringBuilder();
            StringBuilder stderr = new StringBuilder();
            string outCSV = outputPath + @"\fft.csv";
            try
            {
                process.StartInfo.FileName = pythonPath;
                process.StartInfo.Arguments = pythonAppsPath + @"\audiotools.py FFT DVT " + wavFile + " " + outCSV;
                Log("PythonFFT: Calling: " + process.StartInfo.FileName + " " + process.StartInfo.Arguments);
                process.StartInfo.RedirectStandardError = true;
                process.StartInfo.RedirectStandardOutput = true;
                process.StartInfo.WindowStyle = ProcessWindowStyle.Hidden;
                process.StartInfo.CreateNoWindow = true;
                process.StartInfo.UseShellExecute = false;
                process.EnableRaisingEvents = false;
                process.OutputDataReceived += (sender2, eventArgs) => stdout.AppendLine(eventArgs.Data);
                process.ErrorDataReceived += (sender2, eventArgs) => stderr.AppendLine(eventArgs.Data);
                process.Start();
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();
                var processExited = process.WaitForExit(2000 * 10);
                if (processExited == false)
                {
                    process.Kill();
                    Log("PythonFFT: Process timeout");
                }
                else if (process.ExitCode != 0)
                {
                    Log("PythonFFT: Process failed to run with error: " + stderr.ToString());
                }
            }
            catch (Exception ex)
            {
                Log("PythonFFT: Failed to run with: " + ex);
                return;
            }
            process.Close();

            var output = stdout.ToString();
            if (output.Contains("Success") == false)
            {
                Log("PythonFFT: FFT failed to run: " + output);
                return;
            }

            Log("PythonFFT: Successful");

            List<FFTResults> results = new List<FFTResults>();
            ParseFFT(outCSV, ref results);
            return;
        }
        public bool ParseFFT(string filename, ref List<FFTResults> results)
        {
            // Parse the CSV results
            try
            {
                using (TextFieldParser parser = new TextFieldParser(filename))
                {
                    parser.TextFieldType = FieldType.Delimited;
                    parser.SetDelimiters(",");
                    results.Clear();
                    int row = 0;
                    int col = 0;
                    while (!parser.EndOfData)
                    {
                        string[] fields = parser.ReadFields();
                        col = 0;
                        foreach (string field in fields)
                        {
                            if (row == 0)
                            {
                                // Frequency
                                results.Add(new FFTResults(Math.Round(double.Parse(field))));
                            }
                            else if (row % 2 == 0)
                            {
                                // Ignore duplicate frequency row
                            }
                            else
                            {
                                // Amplitude
                                if (col < results.Count)
                                    results[col].AmpdBFS.Add(double.Parse(field));
                                else
                                    Log("ParseFFT: File: " + filename + " Rows:" + row + " Columns:" + col + " out of range: " + results.Count);
                            }
                            col++;
                        }
                        row++;
                    }
                }
                return true;
            }
            catch (Exception ex)
            {
                Log("ParseFFT: Failed to parse CSV: " + ex);
                return false;
            }
        }

        // C# FFT
        private void CSharpFFT(out int sample_rate, out double[] signal, out double[] freq, out double[] result)
        {
            // read .wav file
            OpenWav(wavFile, out sample_rate, out signal);

            // FFT - Input length must be an even power of 2
            int pow2 = (int)(Math.Log(signal.Length) / Math.Log(2));
            int len = (int)Math.Pow(2, pow2);
            //if (len > 16384) len = 16384;
            signal = signal.Take(len).ToArray();

            // remove mean
            double sum = 0;
            foreach (var s in signal) sum += s;
            for (int i = 0; i < len; i++) signal[i] -= sum / len;

            // windowed
            //var window = new FftSharp.Windows.Hanning();
            //signal = window.Apply(signal);

            // FFT
            result = FftSharp.Transform.FFTpower(signal);
            freq = FftSharp.Transform.FFTfreq(sample_rate, result.Length);
        }

        ///////////////////////////////////////////////
        /// C# FFT
        /// ///////////////////////////////////////////
        private void CSharpFFT_Click(object sender, EventArgs e)
        {
            CSharpFFT(out int sample_rate, out double[] signal, out double[] freq, out double[] result);

            // show only freq in integer
            var freq2 = new List<int>();
            var result2 = new List<double>();
            int prev_freq = -1;
            for (int i = 0; i < freq.Length; i++)
            {
                int nfreq = (int)freq[i];
                if (nfreq >= 300 && nfreq != prev_freq)
                {
                    prev_freq = nfreq;
                    freq2.Add(nfreq);
                    result2.Add(result[i]);
                }
            }

            WriteCSV(freq2, result2);   // csv

            WriteExcel(freq2, result2); // excel

            Log("FFT_CS success");
        }
        private void WriteCSV(List<int> freq, List<double> result)
        {
            string outCSV = outputPath + @"\fft_cs.csv";
            using (System.IO.StreamWriter file = new System.IO.StreamWriter(outCSV))
            {
                /*
                // write data horizontally
                file.Write(string.Join(",", freq2));
                file.Write("\n");
                file.Write(string.Join(",", result2));
                */

                // write data vertically
                for (int i = 0; i < freq.Count; i++)
                {
                    file.Write(freq[i].ToString());
                    file.Write(",");
                    file.Write(result[i].ToString());
                    file.Write("\n");
                }
            }
        }
        private void WriteExcel(List<int> freq, List<double> result)
        {
            ExcelPackage.LicenseContext = OfficeOpenXml.LicenseContext.NonCommercial;
            ExcelPackage excel = new ExcelPackage();
            var workSheet = excel.Workbook.Worksheets.Add("FFT_CS");
            for (int i = 0; i < freq.Count; i++)
            {
                workSheet.Cells[i + 1, 1].Value = freq[i];
                workSheet.Cells[i + 1, 2].Value = result[i];
            }

            var chart = workSheet.Drawings.AddChart("FFT", eChartType.XYScatterSmoothNoMarkers);
            string rowA = "A1:A" + freq.Count;
            string rowB = "B1:B" + result.Count;
            chart.Series.Add(workSheet.Cells[rowB], workSheet.Cells[rowA]);
            chart.XAxis.LogBase = 10;
            chart.XAxis.MinValue = 300;
            chart.XAxis.MaxValue = 8000;
            chart.SetPosition(3, 0, 3, 0);
            chart.SetSize(1200, 500);

            string outExcel = outputPath + @"\fft_cs.xlsx";
            if (File.Exists(outExcel)) File.Delete(outExcel);
            FileStream objFileStrm = File.Create(outExcel);
            objFileStrm.Close();
            File.WriteAllBytes(outExcel, excel.GetAsByteArray());
            excel.Dispose();
        }

        // Root Mean Square
        private double RMS(double[] arr)
        {
            double square = 0;
            foreach (var v in arr)
            {
                square += v * v;
            }

            double mean = square / arr.Length;
            double root = Math.Sqrt(mean);
            return root;
        }

        ///////////////////////////////////////////////
        /// C# THD
        /// ///////////////////////////////////////////
        private void CSharpTHD_Click(object sender, EventArgs e)
        {
            CSharpFFT(out int sample_rate, out double[] signal, out double[] freq, out double[] result);

            // max freq
            double freq_main = -1;
            double result_max = double.MinValue;
            for (int i = 0; i < freq.Length; i++)
            {
                if (result_max < result[i])
                {
                    result_max = result[i];
                    freq_main = freq[i];
                }
            }

            // total rms
            double rms_total = RMS(signal);

            double freq_min = freq_main - 50;
            double freq_max = freq_main + 50;
            double[] noise = FftSharp.Filter.BandStop(signal, sample_rate, freq_min, freq_max); // noise
            double rms_noise = RMS(noise);

            double THDN = rms_noise / rms_total;

            Log("THD: Freq[" + freq_main.ToString("0.00") + "Hz] THD-N [" + (THDN * 100).ToString("0.00") + "%, " + (20 * Math.Log10(THDN)).ToString("0.00") + "dBFs]");
        }

        ///////////////////////////////////////////////
        /// Boring stuff
        /// ///////////////////////////////////////////

        public class AcousticMeasurement
        {
            public double THDMeasuredFrequency;
            public double THDMeasuredDbFS;
            public double THDMeasuredPercent;

            public AcousticMeasurement()
            {
            }
        }

        public class FFTResults
        {
            public double Frequency;
            public List<double> AmpdBFS = new List<double>();

            public FFTResults(double freq)
            {
                this.Frequency = freq;
            }
        }

        private void Log(string text)
        {
            LogBox.AppendText(text);
            LogBox.AppendText(Environment.NewLine);
        }

        private void Browse_Click(object sender, EventArgs e)
        {
            using (var fbd = new OpenFileDialog())
            {
                fbd.InitialDirectory = inputPath;
                DialogResult result = fbd.ShowDialog();
                if (result == DialogResult.OK && !string.IsNullOrWhiteSpace(fbd.FileName))
                {
                    wavFile = fbd.FileName;
                    textBox2.Text = wavFile;
                }
            }
        }
        public static double ParsedoubleString(string doublestr)
        {
            try { return double.Parse(doublestr); }
            catch (Exception) { return 0; }
        }

        public static string AddQuotesIfRequired(string path)
        {
            return !string.IsNullOrWhiteSpace(path) ?
                path.Contains(" ") && (!path.StartsWith("\"") && !path.EndsWith("\"")) ?
                    "\"" + path + "\"" : path :
                    string.Empty;
        }

        public static string GetPythonPath(string requiredVersion = "", string maxVersion = "")
        {
            string[] possiblePythonLocations = new string[2] {
                @"HKLM\SOFTWARE\Python\PythonCore\",
                @"HKCU\SOFTWARE\Python\PythonCore\",
            };

            //Version number, install path
            Dictionary<string, string> pythonLocations = new Dictionary<string, string>();

            foreach (string possibleLocation in possiblePythonLocations)
            {
                string regKey = possibleLocation.Substring(0, 4), actualPath = possibleLocation.Substring(5);
                RegistryKey theKey = (regKey == "HKLM" ? Registry.LocalMachine : Registry.CurrentUser);
                RegistryKey theValue = theKey.OpenSubKey(actualPath);
                if (theValue == null)
                    continue;

                foreach (var v in theValue.GetSubKeyNames())
                {
                    RegistryKey productKey = theValue.OpenSubKey(v);
                    if (productKey != null)
                    {
                        try
                        {
                            var installPath = productKey.OpenSubKey("InstallPath");
                            if (installPath == null)
                                continue;
                            string pythonExePath = installPath.GetValue("ExecutablePath").ToString();
                            if (pythonExePath != null && pythonExePath != "")
                            {
                                pythonLocations.Add(v.ToString(), pythonExePath);
                            }
                        }
                        catch
                        {
                            //Install path doesn't exist
                        }
                    }
                }
            }

            if (pythonLocations.Count > 0)
            {
                System.Version desiredVersion = new System.Version(requiredVersion == "" ? "0.0.1" : requiredVersion),
                    maxPVersion = new System.Version(maxVersion == "" ? "999.999.999" : maxVersion);

                string highestVersion = "", highestVersionPath = "";

                foreach (KeyValuePair<string, string> pVersion in pythonLocations)
                {
                    //TODO; if on 64-bit machine, prefer the 64 bit version over 32 and vice versa
                    int index = pVersion.Key.IndexOf("-"); //For x-32 and x-64 in version numbers
                    string formattedVersion = index > 0 ? pVersion.Key.Substring(0, index) : pVersion.Key;

                    System.Version thisVersion = new System.Version(formattedVersion);
                    int comparison = desiredVersion.CompareTo(thisVersion),
                        maxComparison = maxPVersion.CompareTo(thisVersion);

                    if (comparison <= 0)
                    {
                        //Version is greater or equal
                        if (maxComparison >= 0)
                        {
                            desiredVersion = thisVersion;

                            highestVersion = pVersion.Key;
                            highestVersionPath = pVersion.Value;
                        }
                    }
                }
                return highestVersionPath;
            }

            return "";
        }

        private void OpenWav(string filename, out int sample_rate, out double[] signal, double multiplier = 16_000)
        {
            var reader = new NAudio.Wave.AudioFileReader(filename);
            sample_rate = reader.WaveFormat.SampleRate;
            int bytesPerSample = reader.WaveFormat.BitsPerSample / 8;
            int sampleCount = (int)(reader.Length / bytesPerSample);
            int channelCount = reader.WaveFormat.Channels;
            var audio = new List<double>(sampleCount);
            var buffer = new float[sample_rate * channelCount];
            int samplesRead = 0;
            while ((samplesRead = reader.Read(buffer, 0, buffer.Length)) > 0)
                audio.AddRange(buffer.Take(samplesRead).Select(x => x * multiplier));
            signal = audio.ToArray();
            for (int i = 0; i < signal.Length; i++) signal[i] /= 32768.0;
        }
    }
}
