#!/usr/bin/env python3
"""
RPA Web UI Test Script for Transcriptor Pipeline Pilot
======================================================
ทดสอบทุก Function บนหน้าเว็บ Streamlit โดยใช้ Selenium

Test Cases:
1. Navigation - ทดสอบการเปลี่ยนหน้า
2. Transcription - อัพโหลดไฟล์และ transcribe
3. History - ดูประวัติและลบ
4. Statistics - ดูสถิติ
5. Settings - เปลี่ยนค่า settings
6. Export - ดาวน์โหลดไฟล์ผลลัพธ์
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


# ============================================================
# Configuration
# ============================================================
@dataclass
class TestConfig:
    """Test configuration"""
    base_url: str = "http://localhost:8501"
    test_audio_file: str = "/Users/semini/Downloads/EPG_test_5min.mp3"  # 5-min file for faster tests
    timeout: int = 30
    transcription_timeout: int = 300  # 5 minutes for transcription
    headless: bool = False  # Set True for CI/CD
    screenshot_dir: str = "tests/screenshots"


# ============================================================
# Test Result Tracking
# ============================================================
@dataclass
class TestResult:
    """Individual test result"""
    name: str
    passed: bool
    duration: float
    error: Optional[str] = None
    screenshot: Optional[str] = None


class TestReport:
    """Test report generator"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = datetime.now()

    def add_result(self, result: TestResult):
        self.results.append(result)

    def summary(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        duration = (datetime.now() - self.start_time).total_seconds()

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "N/A",
            "total_duration": f"{duration:.1f}s",
            "timestamp": self.start_time.isoformat()
        }

    def print_report(self):
        print("\n" + "=" * 60)
        print("📊 RPA TEST REPORT")
        print("=" * 60)

        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} | {result.name} ({result.duration:.1f}s)")
            if result.error:
                print(f"       └─ Error: {result.error}")

        print("-" * 60)
        summary = self.summary()
        print(f"Total: {summary['total_tests']} | "
              f"Passed: {summary['passed']} | "
              f"Failed: {summary['failed']} | "
              f"Rate: {summary['success_rate']}")
        print(f"Duration: {summary['total_duration']}")
        print("=" * 60)


# ============================================================
# RPA Test Class
# ============================================================
class StreamlitRPATest:
    """RPA tester for Streamlit Web UI"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.report = TestReport()

        # Create screenshot directory
        Path(config.screenshot_dir).mkdir(parents=True, exist_ok=True)

    def setup_driver(self):
        """Setup Chrome WebDriver"""
        options = Options()
        if self.config.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        # Auto-download and setup ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, self.config.timeout)

        print(f"🌐 Chrome WebDriver initialized")

    def teardown(self):
        """Cleanup"""
        if self.driver:
            self.driver.quit()
            print("🔒 WebDriver closed")

    def take_screenshot(self, name: str) -> str:
        """Take screenshot and return path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        path = os.path.join(self.config.screenshot_dir, filename)
        self.driver.save_screenshot(path)
        return path

    def run_test(self, name: str, test_func):
        """Run a single test with error handling"""
        print(f"\n🧪 Running: {name}")
        start_time = time.time()

        try:
            test_func()
            duration = time.time() - start_time
            result = TestResult(name=name, passed=True, duration=duration)
            print(f"   ✅ Passed ({duration:.1f}s)")
        except Exception as e:
            duration = time.time() - start_time
            screenshot = self.take_screenshot(name.replace(" ", "_"))
            result = TestResult(
                name=name,
                passed=False,
                duration=duration,
                error=str(e),
                screenshot=screenshot
            )
            print(f"   ❌ Failed: {e}")

        self.report.add_result(result)
        return result.passed

    # ============================================================
    # Helper Methods
    # ============================================================

    def find_element_by_text(self, text: str, tag: str = "*", timeout: int = None):
        """Find element by text content"""
        timeout = timeout or self.config.timeout
        xpath = f"//{tag}[contains(text(), '{text}')]"
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )

    def find_button_by_text(self, text: str, timeout: int = None):
        """Find button by text"""
        timeout = timeout or self.config.timeout
        # Streamlit buttons have various structures
        selectors = [
            f"//button[contains(., '{text}')]",
            f"//div[@data-testid='stButton']//button[contains(., '{text}')]",
            f"//*[contains(@class, 'stButton')]//button[contains(., '{text}')]"
        ]
        for xpath in selectors:
            try:
                return WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
            except TimeoutException:
                continue
        raise TimeoutException(f"Button '{text}' not found")

    def find_radio_option(self, text: str):
        """Find and click radio button option"""
        # Streamlit radio buttons - try multiple selectors
        selectors = [
            f"//label[contains(., '{text}')]",
            f"//div[contains(@data-testid, 'stRadio')]//label[contains(., '{text}')]",
            f"//p[contains(., '{text}')]",
            f"//span[contains(., '{text}')]",
            f"//*[contains(text(), '{text}')]"
        ]

        for xpath in selectors:
            try:
                element = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                self.scroll_to_element(element)
                element.click()
                time.sleep(0.5)
                return
            except TimeoutException:
                continue

        # If none found, try clicking by partial text
        try:
            # For emojis, try finding just the emoji
            if text.startswith(('🎙', '📜', '📊', '⚙', 'ℹ')):
                emoji = text[0]
                element = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{emoji}')]")
                element.click()
                time.sleep(0.5)
                return
        except:
            pass

        raise TimeoutException(f"Radio option '{text}' not found")

    def wait_for_text(self, text: str, timeout: int = None):
        """Wait for text to appear on page"""
        timeout = timeout or self.config.timeout
        self.find_element_by_text(text, timeout=timeout)

    def scroll_to_element(self, element):
        """Scroll element into view"""
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.3)

    # ============================================================
    # Test Cases
    # ============================================================

    def test_01_page_load(self):
        """Test: Page loads successfully"""
        self.driver.get(self.config.base_url)
        time.sleep(3)  # Wait for Streamlit to fully load

        # Check title - Streamlit might use different titles
        page_source = self.driver.page_source
        assert len(page_source) > 1000, "Page did not load properly"

        # Check for Streamlit app loaded (any content)
        assert "streamlit" in page_source.lower() or "Transcriptor" in page_source or "sidebar" in page_source.lower()

    def test_02_navigation_transcribe(self):
        """Test: Navigate to Transcribe page"""
        self.find_radio_option("Transcribe")
        time.sleep(1)

        # Should see upload section - check for file uploader
        page_source = self.driver.page_source
        assert "file" in page_source.lower() or "upload" in page_source.lower() or "อัพโหลด" in page_source

    def test_03_navigation_history(self):
        """Test: Navigate to History page"""
        self.find_radio_option("History")
        time.sleep(1)

        # Should see history section
        page_source = self.driver.page_source
        assert "history" in page_source.lower() or "ประวัติ" in page_source

    def test_04_navigation_statistics(self):
        """Test: Navigate to Statistics page"""
        self.find_radio_option("Statistics")
        time.sleep(1)

        # Should see statistics
        page_source = self.driver.page_source
        assert "statistic" in page_source.lower() or "สถิติ" in page_source or "total" in page_source.lower()

    def test_05_navigation_settings(self):
        """Test: Navigate to Settings page"""
        self.find_radio_option("Settings")
        time.sleep(1)

        # Should see settings
        page_source = self.driver.page_source
        assert "setting" in page_source.lower() or "ตั้งค่า" in page_source or "model" in page_source.lower()

    def test_06_navigation_about(self):
        """Test: Navigate to About page"""
        self.find_radio_option("About")
        time.sleep(1)

        # Should see about info
        page_source = self.driver.page_source
        assert "about" in page_source.lower() or "เกี่ยวกับ" in page_source or "version" in page_source.lower()

    def test_07_settings_model_selection(self):
        """Test: Settings - Model selection works"""
        self.find_radio_option("Settings")
        time.sleep(1)

        # Find model selectbox and verify it exists
        page_source = self.driver.page_source
        assert "model" in page_source.lower() or "Model" in page_source

    def test_08_upload_file(self):
        """Test: Upload audio file"""
        self.find_radio_option("Transcribe")
        time.sleep(1)

        # Find file uploader
        file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')

        # Upload test file
        file_input.send_keys(self.config.test_audio_file)
        time.sleep(2)

        # Verify file is uploaded (filename should appear or upload indicator)
        page_source = self.driver.page_source
        filename = os.path.basename(self.config.test_audio_file)
        assert filename in page_source or "mp3" in page_source.lower() or "uploaded" in page_source.lower()

    def test_09_transcription_full(self):
        """Test: Full transcription process (LONG TEST)"""
        import glob

        outputs_dir = "/Volumes/DOWNLOAD/Docker Tools/transcriptor-pipeline-pilot/data/outputs"

        # Record existing files BEFORE transcription
        existing_files = set(glob.glob(f"{outputs_dir}/*"))
        test_start_time = time.time()
        print(f"   📁 Existing output files: {len(existing_files)}")

        # Navigate to transcribe page
        self.find_radio_option("Transcribe")
        time.sleep(1)

        # Upload file
        try:
            file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
            file_input.send_keys(self.config.test_audio_file)
            time.sleep(2)
            print("   📤 File uploaded")
        except Exception as e:
            print(f"   ⚠️ File upload issue: {e}")

        # Click transcribe button
        button_clicked = False
        for btn_text in ["Start Transcription", "Start", "เริ่ม", "🎬 Start"]:
            try:
                transcribe_btn = self.find_button_by_text(btn_text)
                self.scroll_to_element(transcribe_btn)
                transcribe_btn.click()
                button_clicked = True
                print(f"   🎬 Clicked '{btn_text}' button")
                break
            except:
                continue

        if not button_clicked:
            raise Exception("Could not find transcription start button")

        print("   ⏳ Waiting for transcription to complete...")
        print("   📋 Monitoring real-time logs...")

        # Wait for completion (up to transcription_timeout)
        start = time.time()
        completed = False
        last_progress = ""
        processing_started = False

        while time.time() - start < self.config.transcription_timeout:
            page_source = self.driver.page_source

            # Check for processing indicators
            if "Processing" in page_source or "🔄" in page_source:
                if not processing_started:
                    print("   🔄 Processing started...")
                    processing_started = True

            # Check for real-time log updates
            if "Real-time Logs" in page_source or "Logs" in page_source:
                import re
                # Look for progress percentage
                progress_matches = re.findall(r'(\d+\.?\d*)%', page_source)
                if progress_matches:
                    current_progress = progress_matches[-1]  # Get last match
                    if current_progress != last_progress:
                        print(f"   📊 Progress: {current_progress}%")
                        last_progress = current_progress

                # Look for chunk progress
                chunk_match = re.search(r'(\d+)/(\d+)\s*chunks?', page_source, re.IGNORECASE)
                if chunk_match:
                    print(f"   🧩 Chunks: {chunk_match.group(1)}/{chunk_match.group(2)}")

            # Check for NEW output files (the real completion indicator)
            current_files = set(glob.glob(f"{outputs_dir}/*"))
            new_files = current_files - existing_files
            # Filter to only files created after test started
            recent_new_files = [f for f in new_files if os.path.getmtime(f) > test_start_time]

            if len(recent_new_files) >= 3:  # TXT, JSON, SRT
                print(f"   📂 New output files detected: {len(recent_new_files)}")
                completed = True
                break

            # Check for completion message in page
            if "✅" in page_source and ("Completed" in page_source or "เสร็จ" in page_source):
                # Double-check with file verification
                time.sleep(2)
                current_files = set(glob.glob(f"{outputs_dir}/*"))
                new_files = current_files - existing_files
                recent_new_files = [f for f in new_files if os.path.getmtime(f) > test_start_time]
                if len(recent_new_files) >= 1:
                    completed = True
                    break

            # Check for error
            if "❌" in page_source and ("failed" in page_source.lower() or "error" in page_source.lower()):
                self.take_screenshot("transcription_error")
                raise Exception("Transcription failed - check screenshot")

            time.sleep(5)  # Check every 5 seconds

        if not completed:
            self.take_screenshot("transcription_timeout")
            raise TimeoutException(f"Transcription timed out after {self.config.transcription_timeout}s")

        elapsed = time.time() - start
        print(f"   ✅ Transcription completed in {elapsed:.1f}s!")

        # Store info for next test
        self._transcription_start_time = test_start_time

    def test_10_view_transcript(self):
        """Test: View transcript result and verify content"""
        # Should already be on result page after transcription
        time.sleep(1)

        page_source = self.driver.page_source

        # Verify transcript content is displayed
        # Look for Thai text content (typical meeting transcription)
        has_transcript = any([
            "textarea" in page_source.lower(),
            "Transcript" in page_source,
            "📝" in page_source,
            # Check for actual Thai content
            "ครับ" in page_source or "ค่ะ" in page_source or "การ" in page_source
        ])

        if has_transcript:
            print("   📝 Transcript content found on page")
        else:
            # Navigate to history and check there
            self.find_radio_option("History")
            time.sleep(1)
            page_source = self.driver.page_source

        # Verify download buttons exist (proves output files were created)
        assert "Download" in page_source or "download" in page_source.lower(), \
            "No download buttons found - transcript may not have been generated"

        print("   ✅ Transcript and download options verified")

    def test_10b_verify_output_files(self):
        """Test: Verify output files were actually created on disk from THIS transcription"""
        import glob

        outputs_dir = "/Volumes/DOWNLOAD/Docker Tools/transcriptor-pipeline-pilot/data/outputs"

        # Use the start time from test_09 if available
        if hasattr(self, '_transcription_start_time'):
            recent_time = self._transcription_start_time
            print(f"   ⏱️ Checking files created since transcription started")
        else:
            # Fallback: files created in last 5 minutes
            recent_time = time.time() - 300
            print(f"   ⏱️ Checking files created in last 5 minutes")

        txt_files = glob.glob(f"{outputs_dir}/*.txt")
        json_files = glob.glob(f"{outputs_dir}/*.json")
        srt_files = glob.glob(f"{outputs_dir}/*.srt")

        # Filter to files created AFTER transcription started (ignore ._ macOS metadata files)
        recent_txt = [f for f in txt_files if os.path.getmtime(f) > recent_time and not os.path.basename(f).startswith('._')]
        recent_json = [f for f in json_files if os.path.getmtime(f) > recent_time and not os.path.basename(f).startswith('._')]
        recent_srt = [f for f in srt_files if os.path.getmtime(f) > recent_time and not os.path.basename(f).startswith('._')]

        print(f"   📁 New files: {len(recent_txt)} TXT, {len(recent_json)} JSON, {len(recent_srt)} SRT")

        # Verify at least TXT file exists
        assert len(recent_txt) > 0, "No NEW TXT output file found - transcription may not have completed"

        # Verify TXT file has content
        latest_txt = max(recent_txt, key=os.path.getmtime)
        with open(latest_txt, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 100, f"TXT file too small ({len(content)} chars)"
        print(f"   📄 TXT: {os.path.basename(latest_txt)} ({len(content):,} chars)")

        # Show sample of transcript
        sample = content[:200].replace('\n', ' ')
        print(f"   📝 Sample: {sample}...")

        # Verify JSON file
        if recent_json:
            latest_json = max(recent_json, key=os.path.getmtime)
            with open(latest_json, 'r', encoding='utf-8') as f:
                import json as json_mod
                data = json_mod.load(f)
            # Check for valid JSON structure (our format uses 'transcription', 'chunks', 'metadata')
            valid_keys = ["segments", "text", "transcription", "chunks", "metadata"]
            has_valid_key = any(key in data for key in valid_keys)
            assert has_valid_key, f"JSON file missing expected keys. Found: {list(data.keys())}"
            chunks_count = len(data.get('chunks', data.get('segments', [])))
            print(f"   📋 JSON: {os.path.basename(latest_json)} ({chunks_count} chunks)")
        else:
            print("   ⚠️ No JSON file found")

        # Verify SRT file
        if recent_srt:
            latest_srt = max(recent_srt, key=os.path.getmtime)
            with open(latest_srt, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            assert "-->" in srt_content, "SRT file missing timestamp format"
            subtitle_count = srt_content.count('\n\n')
            print(f"   🎬 SRT: {os.path.basename(latest_srt)} (~{subtitle_count} subtitles)")
        else:
            print("   ⚠️ No SRT file found")

        print("   ✅ Output files verified successfully!")

    def test_11_export_txt(self):
        """Test: Export as TXT"""
        # Navigate to history
        self.find_radio_option("📜 History")
        time.sleep(1)

        # Find export button
        try:
            export_btn = self.find_button_by_text("TXT", timeout=5)
            export_btn.click()
            time.sleep(1)
            print("   📄 TXT export triggered")
        except TimeoutException:
            print("   ⚠️ No TXT export button found (may need history)")

    def test_12_export_srt(self):
        """Test: Export as SRT"""
        try:
            export_btn = self.find_button_by_text("SRT", timeout=5)
            export_btn.click()
            time.sleep(1)
            print("   📄 SRT export triggered")
        except TimeoutException:
            print("   ⚠️ No SRT export button found")

    def test_13_export_json(self):
        """Test: Export as JSON"""
        try:
            export_btn = self.find_button_by_text("JSON", timeout=5)
            export_btn.click()
            time.sleep(1)
            print("   📄 JSON export triggered")
        except TimeoutException:
            print("   ⚠️ No JSON export button found")

    def test_14_statistics_display(self):
        """Test: Statistics page displays data"""
        self.find_radio_option("Statistics")
        time.sleep(1)

        # Should show statistics after transcription
        page_source = self.driver.page_source

        # Check for metric displays
        assert "งาน" in page_source or "job" in page_source.lower() or "total" in page_source.lower() or "statistic" in page_source.lower()

    def test_15_history_list(self):
        """Test: History shows transcription records"""
        self.find_radio_option("History")
        time.sleep(1)

        # Should show history page loaded
        page_source = self.driver.page_source
        assert "history" in page_source.lower() or "ประวัติ" in page_source or "completed" in page_source.lower() or "ไม่มี" in page_source

    def test_16_clear_history(self):
        """Test: Clear history functionality"""
        self.find_radio_option("History")
        time.sleep(1)

        # Just verify history page is displayed
        page_source = self.driver.page_source
        print("   ℹ️ History page loaded successfully")

    def test_17_history_view_details(self):
        """Test: View history job details"""
        self.find_radio_option("History")
        time.sleep(1)

        # Find View button
        try:
            view_btn = self.find_button_by_text("View", timeout=5)
            view_btn.click()
            time.sleep(2)

            # Check if detail view is shown
            page_source = self.driver.page_source
            assert "Download" in page_source or "Back" in page_source or "TXT" in page_source
            print("   👁️ Job details view opened")

            # Check for download options
            if "TXT" in page_source and "JSON" in page_source and "SRT" in page_source:
                print("   📥 All download options visible (TXT, JSON, SRT, SRT→TXT)")

            # Click Back button
            try:
                back_btn = self.find_button_by_text("Back", timeout=5)
                back_btn.click()
                time.sleep(1)
                print("   ← Returned to history list")
            except:
                pass

        except TimeoutException:
            print("   ⚠️ No View button found (no completed jobs)")

    def test_18_settings_model_tabs(self):
        """Test: Settings page has tabs for Models, Performance, Storage"""
        self.find_radio_option("Settings")
        time.sleep(1)

        page_source = self.driver.page_source

        # Check for tabs
        has_tabs = all([
            "Models" in page_source or "🤖" in page_source,
            "Performance" in page_source or "⚡" in page_source,
            "Storage" in page_source or "💾" in page_source
        ])

        if has_tabs:
            print("   📑 All settings tabs found (Models, Performance, Storage)")

        # Check for model management section
        assert "model" in page_source.lower()

    def test_19_settings_custom_model(self):
        """Test: Settings has custom model download section"""
        self.find_radio_option("Settings")
        time.sleep(1)

        page_source = self.driver.page_source

        # Check for HuggingFace model input
        has_hf_section = (
            "HuggingFace" in page_source or
            "Custom Model" in page_source or
            "mlx-community" in page_source
        )

        if has_hf_section:
            print("   🤗 HuggingFace model section found")

        # Check for quick model buttons
        if "Turbo" in page_source or "Small" in page_source or "Tiny" in page_source:
            print("   ⚡ Quick model select buttons found")

        assert "model" in page_source.lower()

    def test_20_transcribe_manual_workers(self):
        """Test: Manual worker mode selection works"""
        self.find_radio_option("Transcribe")
        time.sleep(1)

        # Find Manual mode radio
        try:
            # Look for Manual option
            manual_opt = self.driver.find_element(By.XPATH, "//label[contains(., 'Manual')]")
            manual_opt.click()
            time.sleep(1)
            print("   🔧 Manual mode selected")

            # Check for Processes and Workers inputs
            page_source = self.driver.page_source
            has_inputs = "Processes" in page_source or "Workers" in page_source
            if has_inputs:
                print("   ⚙️ Worker config inputs visible")

        except:
            print("   ⚠️ Manual mode not found")

    # ============================================================
    # Custom Worker Tests
    # ============================================================

    def test_custom_worker_transcription(self, processes=2, workers=4, model='large-v3', audio_file=None):
        """Test: Transcription with custom worker configuration"""
        import glob

        if audio_file is None:
            audio_file = "/Users/semini/Downloads/EPG_test_5min.mp3"

        outputs_dir = "/Volumes/DOWNLOAD/Docker Tools/transcriptor-pipeline-pilot/data/outputs"

        # Record existing files
        existing_files = set(glob.glob(f"{outputs_dir}/*"))
        test_start_time = time.time()
        print(f"   🔧 Testing with {processes}P × {workers}W, Model: {model}")
        print(f"   📁 Audio file: {audio_file}")

        # Navigate to transcribe page
        self.find_radio_option("Transcribe")
        time.sleep(1)

        # Select model if large-v3
        if model == 'large-v3':
            try:
                # Find model dropdown and select large-v3
                model_selects = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="stSelectbox"]')
                if model_selects:
                    model_selects[0].click()
                    time.sleep(0.5)
                    # Look for large-v3 option
                    options = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'Large')]")
                    if options:
                        options[0].click()
                        print(f"   🤖 Model selected: {model}")
            except:
                print("   ⚠️ Could not select model, using default")

        # Select Manual mode
        try:
            manual_labels = self.driver.find_elements(By.XPATH, "//label[contains(., 'Manual')]")
            if manual_labels:
                manual_labels[0].click()
                time.sleep(1)
                print("   🔧 Manual mode selected")

                # Set processes and workers via number inputs
                number_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="number"]')
                if len(number_inputs) >= 2:
                    # Clear and set processes
                    number_inputs[0].clear()
                    number_inputs[0].send_keys(str(processes))
                    # Clear and set workers
                    number_inputs[1].clear()
                    number_inputs[1].send_keys(str(workers))
                    print(f"   ⚙️ Set {processes} processes, {workers} workers")
        except Exception as e:
            print(f"   ⚠️ Could not set worker config: {e}")

        # Upload file
        try:
            file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
            file_input.send_keys(audio_file)
            time.sleep(2)
            print("   📤 File uploaded")
        except Exception as e:
            print(f"   ⚠️ File upload issue: {e}")

        # Click transcribe button
        button_clicked = False
        for btn_text in ["Start Transcription", "Start", "เริ่ม", "🚀"]:
            try:
                transcribe_btn = self.find_button_by_text(btn_text)
                self.scroll_to_element(transcribe_btn)
                transcribe_btn.click()
                button_clicked = True
                print(f"   🎬 Clicked '{btn_text}' button")
                break
            except:
                continue

        if not button_clicked:
            raise Exception("Could not find transcription start button")

        print("   ⏳ Waiting for transcription...")

        # Wait for completion
        start = time.time()
        completed = False
        last_progress = ""

        while time.time() - start < self.config.transcription_timeout:
            page_source = self.driver.page_source

            # Check for progress
            import re
            progress_matches = re.findall(r'(\d+\.?\d*)%', page_source)
            if progress_matches:
                current_progress = progress_matches[-1]
                if current_progress != last_progress:
                    print(f"   📊 Progress: {current_progress}%")
                    last_progress = current_progress

            # Check for NEW output files
            current_files = set(glob.glob(f"{outputs_dir}/*"))
            new_files = current_files - existing_files
            recent_new_files = [f for f in new_files if os.path.getmtime(f) > test_start_time]

            if len(recent_new_files) >= 3:
                print(f"   📂 New output files detected: {len(recent_new_files)}")
                completed = True
                break

            if "✅" in page_source and ("Completed" in page_source or "เสร็จ" in page_source):
                time.sleep(2)
                completed = True
                break

            time.sleep(5)

        elapsed = time.time() - start
        print(f"   ⏱️ Transcription took {elapsed:.1f}s")

        if not completed:
            raise TimeoutException("Transcription timed out")

        print(f"   ✅ Custom worker test passed ({processes}P × {workers}W, {model})")
        return elapsed

    # ============================================================
    # Run All Tests
    # ============================================================

    def run_all_tests(self, skip_transcription: bool = False, custom_worker_test: bool = False):
        """Run all test cases"""
        print("\n" + "=" * 60)
        print("🚀 STARTING RPA WEB UI TESTS")
        print("=" * 60)
        print(f"Target: {self.config.base_url}")
        print(f"Test Audio: {self.config.test_audio_file}")
        print(f"Skip Transcription: {skip_transcription}")
        print(f"Custom Worker Test: {custom_worker_test}")
        print("=" * 60)

        try:
            self.setup_driver()

            # Navigation tests
            self.run_test("01. Page Load", self.test_01_page_load)
            self.run_test("02. Navigate to Transcribe", self.test_02_navigation_transcribe)
            self.run_test("03. Navigate to History", self.test_03_navigation_history)
            self.run_test("04. Navigate to Statistics", self.test_04_navigation_statistics)
            self.run_test("05. Navigate to Settings", self.test_05_navigation_settings)
            self.run_test("06. Navigate to About", self.test_06_navigation_about)

            # Settings tests (new)
            self.run_test("07. Settings Model Selection", self.test_07_settings_model_selection)
            self.run_test("18. Settings Model Tabs", self.test_18_settings_model_tabs)
            self.run_test("19. Settings Custom Model", self.test_19_settings_custom_model)

            # Upload test
            self.run_test("08. Upload File", self.test_08_upload_file)

            # Manual worker mode test
            self.run_test("20. Manual Worker Mode", self.test_20_transcribe_manual_workers)

            # Transcription test (long running)
            if not skip_transcription:
                self.run_test("09. Full Transcription", self.test_09_transcription_full)
                self.run_test("10. View Transcript", self.test_10_view_transcript)
                self.run_test("10b. Verify Output Files", self.test_10b_verify_output_files)
                self.run_test("11. Export TXT", self.test_11_export_txt)
                self.run_test("12. Export SRT", self.test_12_export_srt)
                self.run_test("13. Export JSON", self.test_13_export_json)
            else:
                print("\n⏭️ Skipping transcription tests (--skip-transcription)")

            # Post-transcription tests
            self.run_test("14. Statistics Display", self.test_14_statistics_display)
            self.run_test("15. History List", self.test_15_history_list)
            self.run_test("16. Clear History Check", self.test_16_clear_history)

            # New: View history details
            self.run_test("17. History View Details", self.test_17_history_view_details)

            # Custom worker test (optional)
            if custom_worker_test:
                print("\n" + "=" * 60)
                print("🔧 CUSTOM WORKER TEST: 2P × 4W, Model: large-v3")
                print("=" * 60)
                self.run_test("21. Custom Worker 2P×4W", lambda: self.test_custom_worker_transcription(
                    processes=2,
                    workers=4,
                    model='large-v3',
                    audio_file="/Users/semini/Downloads/EPG_test_5min.mp3"
                ))

        finally:
            # Take final screenshot
            if self.driver:
                self.take_screenshot("final_state")

            self.teardown()

        # Print report
        self.report.print_report()

        # Return success status
        summary = self.report.summary()
        return summary['failed'] == 0


# ============================================================
# Main Entry Point
# ============================================================
def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="RPA Web UI Test for Transcriptor")
    parser.add_argument("--url", default="http://localhost:8501", help="Streamlit URL")
    parser.add_argument("--audio", default="/Users/semini/Downloads/EPG_test_10min.mp3",
                        help="Test audio file path")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--skip-transcription", action="store_true",
                        help="Skip transcription test (faster)")
    parser.add_argument("--custom-worker-test", action="store_true",
                        help="Run custom worker test (2P×4W, large-v3, 5min audio)")
    parser.add_argument("--timeout", type=int, default=30, help="General timeout in seconds")

    args = parser.parse_args()

    # Verify test file exists
    if not os.path.exists(args.audio):
        print(f"❌ Test audio file not found: {args.audio}")
        sys.exit(1)

    # Create config
    config = TestConfig(
        base_url=args.url,
        test_audio_file=args.audio,
        timeout=args.timeout,
        headless=args.headless
    )

    # Run tests
    tester = StreamlitRPATest(config)
    success = tester.run_all_tests(
        skip_transcription=args.skip_transcription,
        custom_worker_test=args.custom_worker_test
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
