"""
GUI Integration for Block-Level Target Detection
Adds target detection capabilities to studio_gui_engines_v3_14.py
"""

# This code should be added to studio_gui_engines_v3_14.py

# 1. Add import at top of file (around line 25)
INTEGRATION_IMPORTS = '''
try:
    from block_target_detection import BlockTargetAnalysisEngine, BlockTargetDetector
    TARGET_DETECTION_AVAILABLE = True
except ImportError:
    TARGET_DETECTION_AVAILABLE = False
    print("Warning: Target detection not available")
'''

# 2. Add target detection button in block processing frame (around line 245)
TARGET_DETECTION_BUTTON = '''
        # Target Detection Integration
        if TARGET_DETECTION_AVAILABLE:
            target_frame = ttk.Frame(ch_frame)
            target_frame.pack(fill="x", padx=4, pady=2)
            ttk.Button(target_frame, text="🎯 Analyze Targets (SAR/Wreck)", 
                      command=self._analyze_targets, width=25).pack(side="left")
            ttk.Button(target_frame, text="📊 View Reports", 
                      command=self._view_target_reports, width=15).pack(side="left", padx=4)
'''

# 3. Add target analysis methods to App class
TARGET_ANALYSIS_METHODS = '''
    def _analyze_targets(self):
        """Analyze blocks for targets and generate SAR/wreck hunting reports"""
        if not TARGET_DETECTION_AVAILABLE:
            messagebox.showwarning("Not Available", "Target detection functionality not available")
            return
            
        if not hasattr(self, 'block_processor') or not self.block_processor:
            messagebox.showwarning("No Data", "Please run block processing first to generate data for target analysis")
            return
            
        left_ch = int(self.left_channel.get())
        right_ch = int(self.right_channel.get())
        
        def analysis_job(on_progress, check_cancel):
            try:
                on_progress(5, "Initializing target detection engine...")
                
                # Create analysis engine
                engine = BlockTargetAnalysisEngine(self.block_processor)
                
                on_progress(10, f"Analyzing blocks from channels {left_ch} and {right_ch}...")
                
                # Analyze blocks (limit to reasonable number for GUI responsiveness)
                max_blocks = 50  # Adjust based on performance needs
                analyses = engine.analyze_blocks_from_processor(left_ch, right_ch, max_blocks=max_blocks)
                
                on_progress(60, f"Processed {len(analyses)} blocks, generating SAR report...")
                
                # Generate reports
                sar_report = engine.generate_sar_report(analyses)
                
                on_progress(80, "Generating wreck hunting report...")
                wreck_report = engine.generate_wreck_report(analyses)
                
                on_progress(90, "Saving reports...")
                
                # Save reports to output directory
                if hasattr(self, 'last_output_csv_path') and self.last_output_csv_path:
                    output_dir = Path(self.last_output_csv_path).parent
                else:
                    output_dir = Path("outputs")
                
                output_dir.mkdir(exist_ok=True)
                
                # Save JSON reports
                sar_path = output_dir / "sar_analysis_report.json"
                wreck_path = output_dir / "wreck_hunting_report.json"
                
                with open(sar_path, "w") as f:
                    json.dump(sar_report, f, indent=2)
                    
                with open(wreck_path, "w") as f:
                    json.dump(wreck_report, f, indent=2)
                
                # Store reports for viewing
                self.current_sar_report = sar_report
                self.current_wreck_report = wreck_report
                self.current_target_analyses = analyses
                
                on_progress(100, f"✓ Target analysis complete - {len(analyses)} blocks analyzed")
                
                # Log detailed results
                self._q.put(("log", ""))
                self._q.put(("log", "🎯 === TARGET DETECTION RESULTS ==="))
                self._q.put(("log", f"📊 Blocks analyzed: {len(analyses)}"))
                self._q.put(("log", f"🚨 Potential victims found: {len(sar_report['potential_victims'])}"))
                self._q.put(("log", f"🚢 Potential wrecks found: {len(wreck_report['potential_wrecks'])}"))
                self._q.put(("log", f"⚠️  High priority targets: {sar_report['high_priority_targets']}"))
                self._q.put(("log", f"🗂️  Debris fields detected: {wreck_report['debris_fields']}"))
                self._q.put(("log", ""))
                
                # Show SAR recommendations
                if sar_report['search_recommendations']:
                    self._q.put(("log", "🔍 SAR RECOMMENDATIONS:"))
                    for rec in sar_report['search_recommendations']:
                        self._q.put(("log", f"  • {rec}"))
                
                # Show wreck hunting recommendations  
                if wreck_report['wreck_hunting_recommendations']:
                    self._q.put(("log", "⚓ WRECK HUNTING RECOMMENDATIONS:"))
                    for rec in wreck_report['wreck_hunting_recommendations']:
                        self._q.put(("log", f"  • {rec}"))
                
                self._q.put(("log", ""))
                self._q.put(("log", f"📁 Reports saved to: {output_dir}"))
                self._q.put(("log", f"  - SAR Analysis: {sar_path.name}"))
                self._q.put(("log", f"  - Wreck Hunting: {wreck_path.name}"))
                self._q.put(("log", ""))
                self._q.put(("log", "💡 Use 'View Reports' button to see detailed findings"))
                
            except Exception as e:
                on_progress(None, f"Error during target analysis: {str(e)}")
                import traceback
                traceback.print_exc()
                
        self._create_progress_bar("target_analysis", "🎯 Analyzing targets for SAR and wreck hunting...")
        self.process_mgr.start_process("target_analysis", analysis_job)
    
    def _view_target_reports(self):
        """View detailed target detection reports in a popup window"""
        if not hasattr(self, 'current_sar_report') or not self.current_sar_report:
            messagebox.showinfo("No Reports", "Please run target analysis first to generate reports")
            return
            
        # Create report viewing window
        report_window = tk.Toplevel(self)
        report_window.title("🎯 Target Detection Reports - CESARops")
        report_window.geometry("800x600")
        
        # Create notebook for tabbed reports
        notebook = ttk.Notebook(report_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # SAR Report Tab
        sar_frame = ttk.Frame(notebook)
        notebook.add(sar_frame, text="🚨 SAR Analysis")
        
        sar_text = tk.Text(sar_frame, wrap="word", font=("Consolas", 10))
        sar_scroll = ttk.Scrollbar(sar_frame, orient="vertical", command=sar_text.yview)
        sar_text.configure(yscrollcommand=sar_scroll.set)
        
        # Format SAR report
        sar_content = self._format_sar_report(self.current_sar_report)
        sar_text.insert("1.0", sar_content)
        sar_text.config(state="disabled")
        
        sar_text.pack(side="left", fill="both", expand=True)
        sar_scroll.pack(side="right", fill="y")
        
        # Wreck Hunting Report Tab
        wreck_frame = ttk.Frame(notebook)
        notebook.add(wreck_frame, text="⚓ Wreck Hunting")
        
        wreck_text = tk.Text(wreck_frame, wrap="word", font=("Consolas", 10))
        wreck_scroll = ttk.Scrollbar(wreck_frame, orient="vertical", command=wreck_text.yview)
        wreck_text.configure(yscrollcommand=wreck_scroll.set)
        
        # Format wreck report
        wreck_content = self._format_wreck_report(self.current_wreck_report)
        wreck_text.insert("1.0", wreck_content)
        wreck_text.config(state="disabled")
        
        wreck_text.pack(side="left", fill="both", expand=True)
        wreck_scroll.pack(side="right", fill="y")
        
        # Target Details Tab
        if hasattr(self, 'current_target_analyses') and self.current_target_analyses:
            details_frame = ttk.Frame(notebook)
            notebook.add(details_frame, text="📋 Target Details")
            
            details_text = tk.Text(details_frame, wrap="word", font=("Consolas", 9))
            details_scroll = ttk.Scrollbar(details_frame, orient="vertical", command=details_text.yview)
            details_text.configure(yscrollcommand=details_scroll.set)
            
            # Format detailed analysis
            details_content = self._format_target_details(self.current_target_analyses)
            details_text.insert("1.0", details_content)
            details_text.config(state="disabled")
            
            details_text.pack(side="left", fill="both", expand=True)
            details_scroll.pack(side="right", fill="y")
    
    def _format_sar_report(self, report):
        """Format SAR report for display"""
        content = f"""🚨 SEARCH AND RESCUE ANALYSIS REPORT
Generated: {report['timestamp']}
CESARops Target Detection System

📊 SUMMARY
═══════════════════════════════════════════════════════════════
Blocks Analyzed: {report['total_blocks_analyzed']}
Potential Victims: {len(report['potential_victims'])}
High Priority Targets: {report['high_priority_targets']}

"""
        
        if report['potential_victims']:
            content += "🚨 POTENTIAL VICTIM LOCATIONS\n"
            content += "═══════════════════════════════════════════════════════════════\n"
            for i, victim in enumerate(report['potential_victims'], 1):
                content += f"#{i} Block {victim['block']}\n"
                content += f"    Position: ({victim['position'][0]}, {victim['position'][1]})\n"
                content += f"    Confidence: {victim['confidence']:.3f}\n"
                if victim['gps']:
                    content += f"    GPS: {victim['gps'][0]:.6f}, {victim['gps'][1]:.6f}\n"
                content += f"    Priority: {'HIGH' if victim['confidence'] > 0.6 else 'MEDIUM'}\n\n"
        
        if report['search_recommendations']:
            content += "🔍 SEARCH RECOMMENDATIONS\n"
            content += "═══════════════════════════════════════════════════════════════\n"
            for i, rec in enumerate(report['search_recommendations'], 1):
                content += f"{i}. {rec}\n"
        
        content += "\n📋 OPERATIONAL NOTES\n"
        content += "═══════════════════════════════════════════════════════════════\n"
        content += "• Deploy ROV/divers to high-confidence locations first\n"
        content += "• Use GPS coordinates for precise navigation\n"
        content += "• Investigate debris fields systematically\n"
        content += "• Consider environmental factors (current, visibility)\n"
        content += "• Document all findings with photos/video\n"
        
        return content
    
    def _format_wreck_report(self, report):
        """Format wreck hunting report for display"""
        content = f"""⚓ WRECK HUNTING ANALYSIS REPORT
Generated: {report['timestamp']}
CESARops Target Detection System

📊 SUMMARY
═══════════════════════════════════════════════════════════════
Blocks Analyzed: {report['total_blocks_analyzed']}
Potential Wrecks: {len(report['potential_wrecks'])}
Debris Fields: {report['debris_fields']}

"""
        
        if report['potential_wrecks']:
            content += "🚢 POTENTIAL WRECK SITES\n"
            content += "═══════════════════════════════════════════════════════════════\n"
            for i, wreck in enumerate(report['potential_wrecks'], 1):
                content += f"#{i} {wreck['type'].replace('_', ' ').title()}\n"
                content += f"    Block: {wreck['block']}\n"
                content += f"    Size: {wreck['size_meters']:.1f} meters\n"
                content += f"    Confidence: {wreck['confidence']:.3f}\n"
                content += f"    Acoustic Shadow: {'Yes' if wreck['has_shadow'] else 'No'}\n"
                if wreck['gps']:
                    content += f"    GPS: {wreck['gps'][0]:.6f}, {wreck['gps'][1]:.6f}\n"
                priority = "HIGH" if wreck['confidence'] > 0.7 else "MEDIUM" if wreck['confidence'] > 0.5 else "LOW"
                content += f"    Priority: {priority}\n\n"
        
        if report['wreck_hunting_recommendations']:
            content += "⚓ WRECK HUNTING RECOMMENDATIONS\n"
            content += "═══════════════════════════════════════════════════════════════\n"
            for i, rec in enumerate(report['wreck_hunting_recommendations'], 1):
                content += f"{i}. {rec}\n"
        
        content += "\n🗺️ EXPLORATION STRATEGY\n"
        content += "═══════════════════════════════════════════════════════════════\n"
        content += "• Investigate high-confidence targets first\n"
        content += "• Large wrecks (>20m) are priority for historical significance\n"
        content += "• Document wreck orientation and condition\n"
        content += "• Check for debris fields around main wreck site\n"
        content += "• Consider archaeological/historical protocols\n"
        content += "• Safety first - check for hazardous materials\n"
        
        return content
    
    def _format_target_details(self, analyses):
        """Format detailed target analysis for display"""
        content = f"""📋 DETAILED TARGET ANALYSIS
CESARops Block-Level Detection Results

Total Blocks Processed: {len(analyses)}

"""
        
        target_count = 0
        for analysis in analyses:
            if analysis.targets:
                content += f"Block {analysis.block_index} ({len(analysis.targets)} targets)\n"
                content += f"Bottom Type: {analysis.bottom_type}\n"
                content += f"Average Depth: {analysis.average_depth:.1f}m\n"
                content += f"Acoustic Shadows: {len(analysis.acoustic_shadows)}\n"
                content += "─" * 50 + "\n"
                
                for i, target in enumerate(analysis.targets, 1):
                    target_count += 1
                    content += f"  Target {target_count}: {target.target_type.replace('_', ' ').title()}\n"
                    content += f"    Confidence: {target.confidence:.3f}\n"
                    content += f"    Size: {target.size_meters:.2f}m\n"
                    content += f"    Position: ({target.center_x}, {target.center_y})\n"
                    content += f"    Bounding Box: {target.bounding_box}\n"
                    content += f"    Shadow Present: {target.acoustic_shadow}\n"
                    
                    # Show key features
                    if target.features:
                        content += f"    Features:\n"
                        content += f"      - Area: {target.features.get('area', 0):.1f} pixels\n"
                        content += f"      - Aspect Ratio: {target.features.get('aspect_ratio', 0):.2f}\n"
                        content += f"      - Contrast: {target.features.get('contrast', 0):.1f}\n"
                        content += f"      - Mean Intensity: {target.features.get('mean_intensity', 0):.1f}\n"
                    
                    content += "\n"
                
                content += "\n"
        
        if target_count == 0:
            content += "No targets detected in analyzed blocks.\n"
            content += "Consider adjusting detection parameters or analyzing more blocks.\n"
        
        return content
'''

print("Integration code generated!")
print("\\nTo integrate target detection into the GUI:")
print("1. Add the imports at the top of studio_gui_engines_v3_14.py")
print("2. Add the target detection button in the block processing frame")
print("3. Add the target analysis methods to the App class")
print("\\nThis will add:")
print("- 🎯 Analyze Targets button for SAR and wreck hunting")
print("- 📊 View Reports button for detailed analysis")
print("- Tabbed report viewer with SAR, Wreck, and Target details")
print("- Professional report formatting for CESARops program")