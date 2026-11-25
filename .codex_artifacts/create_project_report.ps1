$ErrorActionPreference = 'Stop'

$outputPath = Join-Path $PSScriptRoot '..\UAV_Swarm_Task_Allocation_Project_Report.docx'
$pdfPath = Join-Path $PSScriptRoot 'UAV_Swarm_Task_Allocation_Project_Report_QA.pdf'
$outputPath = [System.IO.Path]::GetFullPath($outputPath)
$pdfPath = [System.IO.Path]::GetFullPath($pdfPath)

$wdAlignLeft = 0
$wdAlignCenter = 1
$wdAlignJustify = 3
$wdPageBreak = 7
$wdStory = 6
$wdFieldPage = 33
$wdFormatDocumentDefault = 16
$wdExportFormatPDF = 17
$navy = 6100503 # Word RGB value for #17365D
$lightBlue = 15790320 # Word RGB value for #F0F5FA
$white = 16777215

$word = $null
$doc = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Add()
    $selection = $word.Selection

    $section = $doc.Sections.Item(1)
    $section.PageSetup.PaperSize = 7 # A4
    $section.PageSetup.TopMargin = $word.CentimetersToPoints(2.54)
    $section.PageSetup.BottomMargin = $word.CentimetersToPoints(2.54)
    $section.PageSetup.LeftMargin = $word.CentimetersToPoints(2.54)
    $section.PageSetup.RightMargin = $word.CentimetersToPoints(2.54)

    $normal = $doc.Styles.Item('Normal')
    $normal.Font.Name = 'Times New Roman'
    $normal.Font.Size = 12
    $normal.ParagraphFormat.LineSpacingRule = 5 # 1.5 lines
    $normal.ParagraphFormat.SpaceAfter = 6

    $footer = $section.Footers.Item(1)
    $footer.Range.ParagraphFormat.Alignment = $wdAlignCenter
    $footer.Range.Font.Name = 'Times New Roman'
    $footer.Range.Font.Size = 10
    $footer.Range.Text = 'Page '
    $footer.Range.Fields.Add($footer.Range, $wdFieldPage) | Out-Null

    function Set-SelectionFormat {
        param([int]$Size = 12, [bool]$Bold = $false, [int]$Alignment = 0, [int]$Before = 0, [int]$After = 6)
        $selection.Font.Name = 'Times New Roman'
        $selection.Font.Size = $Size
        $selection.Font.Bold = [int]$Bold
        $selection.Font.Color = 0
        $selection.ParagraphFormat.Alignment = $Alignment
        $selection.ParagraphFormat.SpaceBefore = $Before
        $selection.ParagraphFormat.SpaceAfter = $After
        $selection.ParagraphFormat.LineSpacingRule = 5
    }

    function Add-Paragraph {
        param([string]$Text, [int]$Size = 12, [bool]$Bold = $false, [int]$Alignment = 0, [int]$Before = 0, [int]$After = 6)
        Set-SelectionFormat -Size $Size -Bold $Bold -Alignment $Alignment -Before $Before -After $After
        $selection.TypeText($Text)
        $selection.TypeParagraph()
    }

    function Add-Bullet {
        param([string]$Text)
        Set-SelectionFormat -Size 12 -Bold $false -Alignment $wdAlignLeft -Before 0 -After 3
        $selection.ParagraphFormat.LeftIndent = $word.CentimetersToPoints(0.65)
        $selection.ParagraphFormat.FirstLineIndent = $word.CentimetersToPoints(-0.35)
        $selection.TypeText([char]0x2022 + ' ' + $Text)
        $selection.TypeParagraph()
        $selection.ParagraphFormat.LeftIndent = 0
        $selection.ParagraphFormat.FirstLineIndent = 0
    }

    function Add-PageBreak {
        $selection.InsertBreak($wdPageBreak)
    }

    function Add-Chapter {
        param([string]$Title)
        Add-PageBreak
        Set-SelectionFormat -Size 16 -Bold $true -Alignment $wdAlignLeft -Before 0 -After 16
        $selection.Style = $doc.Styles.Item('Heading 1')
        $selection.Font.Name = 'Times New Roman'
        $selection.Font.Color = 0
        $selection.TypeText($Title)
        $selection.TypeParagraph()
        $selection.Style = $doc.Styles.Item('Normal')
    }

    function Add-Subheading {
        param([string]$Title)
        Set-SelectionFormat -Size 13 -Bold $true -Alignment $wdAlignLeft -Before 12 -After 6
        $selection.Style = $doc.Styles.Item('Heading 2')
        $selection.Font.Name = 'Times New Roman'
        $selection.Font.Color = 0
        $selection.TypeText($Title)
        $selection.TypeParagraph()
        $selection.Style = $doc.Styles.Item('Normal')
    }

    function Add-Table {
        param([string[]]$Headers, [object[]]$Rows, [double[]]$Widths = $null)
        $columns = $Headers.Count
        $table = $doc.Tables.Add($selection.Range, $Rows.Count + 1, $columns)
        $table.Borders.Enable = 1
        $table.AllowAutoFit = $true
        for ($col = 1; $col -le $columns; $col++) {
            $cell = $table.Cell(1, $col)
            $cell.Range.Text = [string]$Headers[$col - 1]
            $cell.Range.Font.Name = 'Times New Roman'
            $cell.Range.Font.Size = 10
            $cell.Range.Font.Bold = 1
            $cell.Range.Font.Color = $white
            $cell.Shading.BackgroundPatternColor = $navy
            $cell.VerticalAlignment = 1
            $cell.Range.ParagraphFormat.Alignment = $wdAlignCenter
            if ($Widths) { $cell.Width = $word.CentimetersToPoints($Widths[$col - 1]) }
        }
        for ($row = 0; $row -lt $Rows.Count; $row++) {
            for ($col = 0; $col -lt $columns; $col++) {
                $cell = $table.Cell($row + 2, $col + 1)
                $cell.Range.Text = [string]$Rows[$row][$col]
                $cell.Range.Font.Name = 'Times New Roman'
                $cell.Range.Font.Size = 10
                $cell.Range.Font.Color = 0
                $cell.VerticalAlignment = 1
                if ($row % 2 -eq 1) { $cell.Shading.BackgroundPatternColor = $lightBlue }
                if ($col -eq 0) { $cell.Range.ParagraphFormat.Alignment = $wdAlignLeft } else { $cell.Range.ParagraphFormat.Alignment = $wdAlignCenter }
                if ($Widths) { $cell.Width = $word.CentimetersToPoints($Widths[$col]) }
            }
        }
        $selection.SetRange($table.Range.End, $table.Range.End)
        $selection.TypeParagraph()
        return $table
    }

    function Add-ArchitectureFigure {
        $table = $doc.Tables.Add($selection.Range, 1, 5)
        $table.Borders.Enable = 1
        $labels = @('Local UAV observations', 'Shared MAPPO actor', 'Task actions', 'UAV task environment', 'Reward and PPO update')
        for ($index = 1; $index -le 5; $index++) {
            $cell = $table.Cell(1, $index)
            $cell.Range.Text = $labels[$index - 1]
            $cell.Range.Font.Name = 'Times New Roman'
            $cell.Range.Font.Size = 9
            $cell.Range.Font.Bold = 1
            $cell.Range.ParagraphFormat.Alignment = $wdAlignCenter
            $cell.VerticalAlignment = 1
            $cell.Shading.BackgroundPatternColor = $lightBlue
        }
        $selection.SetRange($table.Range.End, $table.Range.End)
        $selection.TypeParagraph()
        Add-Paragraph -Text 'Figure 3.1  Communication aware MAPPO task allocation architecture' -Size 10 -Bold $false -Alignment $wdAlignCenter -Before 0 -After 10
    }

    # Cover page
    Add-Paragraph -Text '[UNIVERSITY NAME]' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 40 -After 10
    Add-Paragraph -Text '[DEPARTMENT NAME]' -Size 14 -Bold $true -Alignment $wdAlignCenter -Before 0 -After 70
    Add-Paragraph -Text 'COMMUNICATION AWARE ADAPTIVE MAPPO FOR DYNAMIC UAV SWARM TASK ALLOCATION' -Size 20 -Bold $true -Alignment $wdAlignCenter -Before 0 -After 30
    Add-Paragraph -Text 'Project Report' -Size 15 -Bold $true -Alignment $wdAlignCenter -Before 0 -After 18
    Add-Paragraph -Text 'Submitted in partial fulfilment of the requirements for the award of the degree of' -Size 12 -Bold $false -Alignment $wdAlignCenter -Before 0 -After 6
    Add-Paragraph -Text '[DEGREE NAME]' -Size 14 -Bold $true -Alignment $wdAlignCenter -Before 0 -After 50
    Add-Paragraph -Text 'Submitted by' -Size 12 -Bold $false -Alignment $wdAlignCenter -Before 0 -After 6
    Add-Paragraph -Text '[STUDENT NAME]' -Size 14 -Bold $true -Alignment $wdAlignCenter -Before 0 -After 4
    Add-Paragraph -Text '[ENROLLMENT NUMBER]' -Size 12 -Bold $false -Alignment $wdAlignCenter -Before 0 -After 35
    Add-Paragraph -Text 'Under the guidance of' -Size 12 -Bold $false -Alignment $wdAlignCenter -Before 0 -After 6
    Add-Paragraph -Text '[MENTOR NAME]' -Size 14 -Bold $true -Alignment $wdAlignCenter -Before 0 -After 55
    Add-Paragraph -Text '[MONTH YEAR]' -Size 12 -Bold $true -Alignment $wdAlignCenter -Before 0 -After 0

    # Preliminary pages
    Add-PageBreak
    Add-Paragraph -Text 'DECLARATION' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 28
    Add-Paragraph -Text 'I hereby declare that the project report entitled Communication Aware Adaptive MAPPO for Dynamic UAV Swarm Task Allocation is my original work carried out under the guidance of [MENTOR NAME]. This report has not been submitted, in whole or in part, to any other university or institution for the award of any degree or diploma.' -Alignment $wdAlignJustify -After 36
    Add-Paragraph -Text 'Place: [CITY]' -After 6
    Add-Paragraph -Text 'Date: [DATE]' -After 38
    Add-Paragraph -Text 'Signature of Student: ______________________________' -Alignment $wdAlignRight -After 6
    Add-Paragraph -Text 'Name: [STUDENT NAME]' -Alignment $wdAlignRight -After 6
    Add-Paragraph -Text 'Enrollment No.: [ENROLLMENT NUMBER]' -Alignment $wdAlignRight -After 0

    Add-PageBreak
    Add-Paragraph -Text 'CERTIFICATE' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 28
    Add-Paragraph -Text 'This is to certify that the project report entitled Communication Aware Adaptive MAPPO for Dynamic UAV Swarm Task Allocation is a bona fide work carried out by [STUDENT NAME], Enrollment No. [ENROLLMENT NUMBER], under my supervision during the academic session [ACADEMIC YEAR].' -Alignment $wdAlignJustify -After 40
    Add-Paragraph -Text 'Signature of Mentor: ______________________________' -Alignment $wdAlignRight -After 6
    Add-Paragraph -Text 'Name: [MENTOR NAME]' -Alignment $wdAlignRight -After 6
    Add-Paragraph -Text 'Designation and Department: [DETAILS]' -Alignment $wdAlignRight -After 38
    Add-Paragraph -Text 'Head of Department: ______________________________' -After 6
    Add-Paragraph -Text 'Name and Seal: [DETAILS]' -After 0

    Add-PageBreak
    Add-Paragraph -Text 'ACKNOWLEDGEMENT' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 28
    Add-Paragraph -Text 'I express my sincere gratitude to [MENTOR NAME] for guidance, technical direction, and constructive feedback throughout this project. I thank the faculty members of [DEPARTMENT NAME] for the resources and academic environment that supported this work. I am also grateful to my peers and family for their encouragement during the design, implementation, testing, and documentation of the project.' -Alignment $wdAlignJustify -After 48
    Add-Paragraph -Text '[STUDENT NAME]' -Alignment $wdAlignRight -Bold $true -After 0

    Add-PageBreak
    Add-Paragraph -Text 'ABSTRACT' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 22
    Add-Paragraph -Text 'Dynamic task allocation in unmanned aerial vehicle swarms is challenging because a policy must complete distributed tasks while preserving communication among UAVs. This project implements a communication aware adaptive multi agent proximal policy optimization approach, called AC MAPPO, and compares it with RDPSO and a neighborhood aware QRDPSO baseline. The MAPPO actors use local position, energy, task, and communication observations, while a centralized critic uses the global swarm state during training. An adaptive communication penalty increases when swarm connectivity deteriorates.' -Alignment $wdAlignJustify -After 8
    Add-Paragraph -Text 'Across 250 matched headless evaluation runs per algorithm, AC MAPPO achieved 71.7 percent task completion, 60.3 percent mean connectivity, and 0.21 disconnected UAVs at the final step. It improved task completion and connectivity over QRDPSO, which achieved 60.9 percent task completion and 51.9 percent connectivity. RDPSO completed all tasks more quickly but produced substantially lower connectivity. The project also integrates the trained actor into a Webots visualization using a portable NumPy policy file. The results show a communication efficiency trade off and identify sim to simulator transfer as an area for further work.' -Alignment $wdAlignJustify -After 14
    Add-Paragraph -Text 'Keywords: UAV swarm, dynamic task allocation, MAPPO, multi agent reinforcement learning, connectivity aware control, Webots.' -Bold $true -Alignment $wdAlignJustify -After 0

    Add-PageBreak
    Add-Paragraph -Text 'TABLE OF CONTENTS' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 18
    $tocRange = $selection.Range
    $tocRange.Fields.Add($tocRange, -1, 'TOC \o "1-2" \h \z \u', $true) | Out-Null
    $selection.SetRange($doc.Content.End - 1, $doc.Content.End - 1)
    $selection.TypeParagraph()

    Add-PageBreak
    Add-Paragraph -Text 'LIST OF FIGURES' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 18
    Add-Paragraph -Text 'Figure 3.1  Communication aware MAPPO task allocation architecture' -After 5
    Add-Paragraph -Text 'Figure 5.1  Experimental comparison workflow' -After 0

    Add-PageBreak
    Add-Paragraph -Text 'LIST OF TABLES' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 18
    Add-Paragraph -Text 'Table 3.1  State action and reward design' -After 5
    Add-Paragraph -Text 'Table 4.1  Software module implementation' -After 5
    Add-Paragraph -Text 'Table 5.1  Headless evaluation results' -After 5
    Add-Paragraph -Text 'Table 5.2  Webots visual simulation log summary' -After 0

    Add-PageBreak
    Add-Paragraph -Text 'LIST OF ABBREVIATIONS' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 18
    Add-Table -Headers @('Abbreviation', 'Meaning') -Rows @(
        @('AC MAPPO', 'Adaptive Communication Aware Multi Agent Proximal Policy Optimization'),
        @('CTDE', 'Centralized Training and Decentralized Execution'),
        @('GAE', 'Generalized Advantage Estimation'),
        @('MARL', 'Multi Agent Reinforcement Learning'),
        @('MAPPO', 'Multi Agent Proximal Policy Optimization'),
        @('PSO', 'Particle Swarm Optimization'),
        @('QRDPSO', 'Neighborhood aware quantum inspired RDPSO extension'),
        @('RDPSO', 'Baseline PSO style waypoint optimizer'),
        @('UAV', 'Unmanned Aerial Vehicle')
    ) -Widths @(3.2, 12.0)

    # Chapter 1
    Add-Chapter 'CHAPTER 1  INTRODUCTION'
    Add-Subheading '1.1 Introduction'
    Add-Paragraph -Text 'UAV swarms can distribute sensing, inspection, surveillance, search, and delivery tasks over a geographic area. Their usefulness depends on coordinated task allocation: every UAV must decide which task to approach without creating excessive travel, repeated assignment, or loss of communication. A connectivity aware allocation method is especially important when UAVs exchange observations, mission status, or safety information through a limited range communication graph.' -Alignment $wdAlignJustify
    Add-Subheading '1.2 Problem Statement'
    Add-Paragraph -Text 'The project addresses dynamic UAV task allocation under communication constraints. The core problem is to assign available tasks to multiple UAVs while maximizing completed tasks and maintaining a connected swarm. A conventional optimizer can reduce distance but may separate UAVs. A reinforcement learning policy can adapt decisions over time, but it must be rewarded for both mission progress and communication preservation.' -Alignment $wdAlignJustify
    Add-Subheading '1.3 Objectives'
    Add-Bullet -Text 'Implement and compare RDPSO, QRDPSO, and AC MAPPO for UAV task allocation.'
    Add-Bullet -Text 'Model direct communication links, multi hop connectivity, task completion, distance, and energy.'
    Add-Bullet -Text 'Develop communication aware observations and an adaptive communication reward for MAPPO.'
    Add-Bullet -Text 'Evaluate the algorithms on matched random scenarios and visualize trained policy execution in Webots.'
    Add-Subheading '1.4 Project Contribution to Sustainable Development Goals'
    Add-Paragraph -Text 'The project contributes to SDG 9, Industry Innovation and Infrastructure, by developing an intelligent multi UAV coordination framework. It supports SDG 11, Sustainable Cities and Communities, through potential applications in inspection, emergency response, and infrastructure monitoring. It also supports SDG 13, Climate Action, because coordinated UAVs can improve environmental monitoring and disaster assessment while avoiding wasteful travel.' -Alignment $wdAlignJustify
    Add-Subheading '1.5 Organization of the Report'
    Add-Paragraph -Text 'Chapter 2 presents the background. Chapter 3 describes the proposed communication aware MAPPO approach. Chapter 4 documents the implementation. Chapter 5 reports results and discussion. Chapter 6 concludes the work and identifies future directions.' -Alignment $wdAlignJustify

    # Chapter 2
    Add-Chapter 'CHAPTER 2  BACKGROUND'
    Add-Subheading '2.1 UAV Swarm Task Allocation'
    Add-Paragraph -Text 'In task allocation, a swarm maps UAV capabilities and positions to a set of pending tasks. A useful allocation balances coverage, travel cost, completion time, energy, and communication. This project uses a lightweight two dimensional allocation environment with fixed altitude, allowing the focus to remain on allocation rather than low level flight control.' -Alignment $wdAlignJustify
    Add-Subheading '2.2 Particle Swarm Optimization Baselines'
    Add-Paragraph -Text 'Particle swarm optimization represents candidate solutions as particles that move according to inertia, individual experience, and social information. RDPSO is used as the baseline waypoint optimizer. QRDPSO extends this behavior with a neighborhood term derived from the current communication graph. The current QRDPSO code is an isolated engineering reconstruction whose neighborhood term can be replaced when the exact source paper equations are finalized.' -Alignment $wdAlignJustify
    Add-Subheading '2.3 Multi Agent Reinforcement Learning and MAPPO'
    Add-Paragraph -Text 'Multi agent reinforcement learning allows policies to improve through interaction with an environment. MAPPO applies proximal policy optimization to cooperative multi agent settings. It uses centralized training and decentralized execution: the critic can see the global state during training, while each actor uses only local observations during execution. This separation is well suited to UAV swarms where global information may be available during offline training but is not guaranteed at deployment.' -Alignment $wdAlignJustify
    Add-Subheading '2.4 Communication Constraints'
    Add-Paragraph -Text 'A direct communication edge between UAV i and UAV j exists when their distance is not greater than the communication range. The adjacency matrix is used to calculate direct link ratio, connected components, and disconnected UAVs. The proposed policy includes these communication features in the local observation and uses connectivity to adapt the communication penalty.' -Alignment $wdAlignJustify

    # Chapter 3
    Add-Chapter 'CHAPTER 3  PROPOSED WORK'
    Add-Subheading '3.1 Proposed Approach'
    Add-Paragraph -Text 'The proposed method is Adaptive Communication Aware MAPPO, abbreviated AC MAPPO. It combines a shared decentralized actor, a centralized critic, communication aware local observations, and an adaptive reward penalty. The actor chooses a task or an idle action for each UAV. The critic estimates the value of the joint swarm state during training.' -Alignment $wdAlignJustify
    Add-ArchitectureFigure
    Add-Subheading '3.2 State Action and Reward Design'
    Add-Table -Headers @('Element', 'Design in this project') -Rows @(
        @('Actor observation', 'Own normalized x y position, energy, degree, component size, link ratio, and relative task features'),
        @('Global critic state', 'All UAV positions and energies, task positions and completion states, link ratio, and component count'),
        @('Action', 'Select one of three tasks or choose idle'),
        @('Connectivity', 'Direct link ratio and multi hop connected components from the distance graph'),
        @('Reward', 'Task completion reward less travel, disconnection, and adaptive communication penalties')
    ) -Widths @(4.0, 11.2)
    Add-Paragraph -Text 'The adaptive communication penalty is defined as lambda c of t equals lambda c base plus alpha multiplied by one minus connectivity of t. When connectivity falls, the penalty becomes larger. This encourages the policy to preserve links when the swarm is vulnerable to fragmentation.' -Alignment $wdAlignJustify
    Add-Subheading '3.3 MAPPO Update Procedure'
    Add-Paragraph -Text 'Training collects state, action, log probability, reward, value, and termination records in an on policy rollout buffer. Generalized advantage estimation calculates advantages. The PPO update compares new and previous action probabilities using a clipped objective, combines policy loss with value loss and entropy regularization, and applies gradient clipping for stable learning.' -Alignment $wdAlignJustify
    Add-Subheading '3.4 Decentralized Webots Execution'
    Add-Paragraph -Text 'The trained shared actor is exported from a PyTorch checkpoint to a NumPy policy file. Webots builds the same local observation layout used during training and selects the highest scoring unmasked action for each UAV. The centralized critic is not used in Webots execution.' -Alignment $wdAlignJustify

    # Chapter 4
    Add-Chapter 'CHAPTER 4  IMPLEMENTATION DETAILS'
    Add-Subheading '4.1 Software Structure'
    Add-Table -Headers @('Module', 'Implementation responsibility') -Rows @(
        @('qrdpso', 'RDPSO and QRDPSO baselines, task allocation helper, and connectivity utilities'),
        @('environment', 'Common UAV task allocation simulator, observations, reward, and action masks'),
        @('mappo networks', 'Shared actor and centralized critic neural networks'),
        @('mappo rollout and trainer', 'GAE rollout storage, PPO updates, training, and model export'),
        @('experiments', 'Repeated seed based comparison and CSV summary generation'),
        @('Webots supervisor', 'Sequential RDPSO, QRDPSO, and AC MAPPO visualization with mission logging')
    ) -Widths @(4.4, 10.8)
    Add-Subheading '4.2 Training Configuration'
    Add-Paragraph -Text 'The default environment has three UAVs, three tasks, an arena size of 10 units, a communication range of 5.5 units, a speed of 0.35 units per step, a maximum of 80 steps per episode, and an energy budget of 40 units. The shared actor and critic use two hidden layers of 128 units with hyperbolic tangent activation. MAPPO uses a learning rate of 0.0003, discount factor 0.99, GAE lambda 0.95, PPO clipping ratio 0.2, and four update epochs.' -Alignment $wdAlignJustify
    Add-Subheading '4.3 Experiment Execution'
    Add-Paragraph -Text 'The comparison script trains a model for each random seed and evaluates RDPSO, QRDPSO, and AC MAPPO on the same generated scenarios. Raw per run metrics are stored in comparison raw CSV, while aggregated mean and sample standard deviation values are stored in comparison summary CSV. Webots logs visual simulation metrics to mission log CSV.' -Alignment $wdAlignJustify
    Add-Subheading '4.4 Reproducibility'
    Add-Paragraph -Text 'The reported headless experiment used five training seeds, 600 training episodes per seed, and 50 evaluation episodes per seed. This produced 250 evaluation runs for each algorithm. Repeating the experiment with the same configuration and seeds supports direct verification of the reported summary.' -Alignment $wdAlignJustify

    # Chapter 5
    Add-Chapter 'CHAPTER 5  RESULTS AND DISCUSSION'
    Add-Subheading '5.1 Evaluation Metrics'
    Add-Paragraph -Text 'The evaluation measures task completion rate, mission steps, total distance, mean connectivity, final disconnected UAVs, and accumulated allocation computation time. Higher task completion and connectivity are desirable, whereas lower distance, mission steps, and disconnections are desirable.' -Alignment $wdAlignJustify
    Add-Subheading '5.2 Headless Evaluation Results'
    Add-Table -Headers @('Method', 'Task completion percent', 'Mean connectivity percent', 'Disconnected UAVs', 'Mission steps', 'Distance') -Rows @(
        @('RDPSO', '100.0 +/- 0.0', '15.1 +/- 15.7', '1.66 +/- 0.52', '31.16 +/- 9.80', '21.02 +/- 7.06'),
        @('QRDPSO', '60.9 +/- 37.0', '51.9 +/- 30.9', '0.54 +/- 0.69', '67.22 +/- 19.05', '52.10 +/- 21.12'),
        @('AC MAPPO', '71.7 +/- 33.0', '60.3 +/- 25.5', '0.21 +/- 0.46', '65.11 +/- 19.58', '53.28 +/- 21.92')
    ) -Widths @(2.2, 2.8, 3.0, 2.4, 2.2, 2.2)
    Add-Paragraph -Text 'Table 5.1  Mean plus or minus sample standard deviation across 250 matched evaluation runs per algorithm' -Size 10 -Alignment $wdAlignCenter -After 10
    Add-Paragraph -Text 'AC MAPPO improves task completion over QRDPSO by 10.8 percentage points and raises mean connectivity from 51.9 percent to 60.3 percent. It also reduces final disconnected UAVs from 0.54 to 0.21. These results support the communication aware contribution when compared with QRDPSO.' -Alignment $wdAlignJustify
    Add-Paragraph -Text 'RDPSO remains the strongest method for pure task completion, travel distance, and mission duration. Its performance is obtained at the cost of communication: mean connectivity is only 15.1 percent and the final swarm commonly contains one or more disconnected UAVs. Therefore the current results demonstrate a task efficiency versus communication resilience trade off rather than a universal AC MAPPO win.' -Alignment $wdAlignJustify
    Add-Subheading '5.3 Webots Visual Simulation'
    Add-Table -Headers @('Method', 'Completed tasks', 'Cycles', 'Distance', 'Final connectivity', 'Final disconnected UAVs') -Rows @(
        @('RDPSO', '3 of 3', '87', '19.31', '33.3 percent', '1'),
        @('QRDPSO', '3 of 3', '340', '74.20', '33.3 percent', '1'),
        @('AC MAPPO', '0 of 3', '115', '120.75', '100.0 percent', '0')
    ) -Widths @(2.2, 2.3, 2.0, 2.2, 3.1, 3.2)
    Add-Paragraph -Text 'Table 5.2  Latest Webots mission log summary' -Size 10 -Alignment $wdAlignCenter -After 10
    Add-Paragraph -Text 'The Webots log confirms that the exported AC MAPPO actor loads and moves the UAVs. In this fixed visual scenario, however, it preserves full connectivity while completing no tasks before energy depletion. This is a transfer limitation, not evidence of successful Webots task allocation. The model should be retrained on Webots like task layouts and evaluated across all saved seeds before using Webots results as final performance evidence.' -Alignment $wdAlignJustify
    Add-Subheading '5.4 Limitations'
    Add-Bullet -Text 'The current environment uses simplified planar movement and distance based communication.'
    Add-Bullet -Text 'QRDPSO should be updated if exact paper equations and parameters become available.'
    Add-Bullet -Text 'MAPPO and QRDPSO show high variability across random scenarios.'
    Add-Bullet -Text 'The current trained policy does not yet transfer successfully to the fixed Webots mission.'

    # Chapter 6
    Add-Chapter 'CHAPTER 6  CONCLUSIONS AND FUTURE WORK'
    Add-Subheading '6.1 Conclusions'
    Add-Paragraph -Text 'This project implemented a modular UAV swarm task allocation framework with RDPSO, QRDPSO, and AC MAPPO. The proposed method combines communication aware observations with an adaptive connectivity penalty. On the matched headless experiment, AC MAPPO achieved higher task completion and stronger communication metrics than QRDPSO. RDPSO remained more efficient for task completion but fragmented the swarm. The outcome demonstrates that explicit communication awareness changes allocation behavior and creates a measurable efficiency resilience trade off.' -Alignment $wdAlignJustify
    Add-Subheading '6.2 Future Work'
    Add-Bullet -Text 'Tune task completion and communication reward weights to improve MAPPO completion without losing connectivity.'
    Add-Bullet -Text 'Train with deterministic and randomized scenarios that represent the Webots world.'
    Add-Bullet -Text 'Run ablations for communication observation only, adaptive reward only, and their combined effect.'
    Add-Bullet -Text 'Add dynamic task arrivals, UAV failures, obstacles, and larger swarm sizes.'
    Add-Bullet -Text 'Report confidence intervals and statistical significance tests over independent training runs.'

    # References
    Add-PageBreak
    Add-Paragraph -Text 'REFERENCES' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 20
    Add-Paragraph -Text '[1] J. Kennedy and R. Eberhart, Particle Swarm Optimization, Proceedings of the IEEE International Conference on Neural Networks, 1995, pp. 1942-1948.' -Alignment $wdAlignLeft -After 8
    Add-Paragraph -Text '[2] J. Schulman, F. Wolski, P. Dhariwal, A. Radford, and O. Klimov, Proximal Policy Optimization Algorithms, arXiv preprint arXiv:1707.06347, 2017.' -Alignment $wdAlignLeft -After 8
    Add-Paragraph -Text '[3] C. Yu et al., The Surprising Effectiveness of PPO in Cooperative Multi Agent Games, arXiv preprint arXiv:2103.01955, 2022.' -Alignment $wdAlignLeft -After 8
    Add-Paragraph -Text '[4] Cyberbotics, Webots User Guide and Reference Manual, accessed 2026.' -Alignment $wdAlignLeft -After 8
    Add-Paragraph -Text '[5] Source QRDPSO task distribution research paper supplied for this project. Insert the complete bibliographic reference from the final selected paper before submission.' -Alignment $wdAlignLeft -After 0

    # Annexure
    Add-PageBreak
    Add-Paragraph -Text 'ANNEXURE' -Size 16 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 16
    Add-Paragraph -Text 'PART A  STUDENT INFORMATION' -Size 14 -Bold $true -Alignment $wdAlignCenter -Before 0 -After 14
    Add-Table -Headers @('Field', 'Information') -Rows @(
        @('Student Name', '[STUDENT NAME]'),
        @('Enrollment Number', '[ENROLLMENT NUMBER]'),
        @('Programme and Semester', '[PROGRAMME AND SEMESTER]'),
        @('Department', '[DEPARTMENT NAME]'),
        @('Academic Session', '[ACADEMIC YEAR]'),
        @('Project Title', 'Communication Aware Adaptive MAPPO for Dynamic UAV Swarm Task Allocation'),
        @('Student Email and Phone', '[EMAIL]  [PHONE]'),
        @('Mentor Name and Designation', '[MENTOR NAME AND DESIGNATION]')
    ) -Widths @(5.0, 10.2)
    Add-Subheading 'Student and Mentor Proforma'
    Add-Table -Headers @('Item', 'Student Entry', 'Mentor Remarks') -Rows @(
        @('Problem statement finalized', '[DATE OR STATUS]', '[REMARKS]'),
        @('Literature review completed', '[DATE OR STATUS]', '[REMARKS]'),
        @('Baseline implementation completed', '[DATE OR STATUS]', '[REMARKS]'),
        @('MAPPO implementation completed', '[DATE OR STATUS]', '[REMARKS]'),
        @('Experiments and results completed', '[DATE OR STATUS]', '[REMARKS]'),
        @('Report status', '[DATE OR STATUS]', '[REMARKS]')
    ) -Widths @(5.5, 4.2, 5.5)
    Add-Paragraph -Text 'Student Signature: ______________________________' -After 16
    Add-Paragraph -Text 'Mentor Signature: ______________________________' -After 0

    Add-PageBreak
    Add-Paragraph -Text 'MID TERM EVALUATION' -Size 14 -Bold $true -Alignment $wdAlignCenter -Before 12 -After 16
    Add-Table -Headers @('Evaluation Criterion', 'Maximum Marks', 'Marks Awarded', 'Evaluator Remarks') -Rows @(
        @('Problem definition and objectives', '10', '', ''),
        @('Literature review and background study', '10', '', ''),
        @('Methodology and technical design', '20', '', ''),
        @('Implementation progress', '20', '', ''),
        @('Experimental design and initial results', '20', '', ''),
        @('Presentation documentation and response', '10', '', ''),
        @('Total', '90', '', '')
    ) -Widths @(6.3, 2.5, 2.8, 3.6)
    Add-Paragraph -Text 'Evaluator Name: ______________________________' -Before 22 -After 8
    Add-Paragraph -Text 'Signature and Date: ______________________________' -After 0

    # Update fields and save
    foreach ($field in $doc.Fields) { try { $field.Update() | Out-Null } catch {} }
    $doc.SaveAs([ref]$outputPath, [ref]$wdFormatDocumentDefault)
    $doc.ExportAsFixedFormat($pdfPath, $wdExportFormatPDF)
    Write-Output "DOCX=$outputPath"
    Write-Output "PDF=$pdfPath"
}
finally {
    if ($doc) { $doc.Close() }
    if ($word) { $word.Quit() }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
