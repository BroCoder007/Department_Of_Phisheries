// Create DataFolder (Text) and UseBackend (True/False) parameters first.

// Query: ClassSummary
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/class_summary.csv"]) else File.Contents(DataFolder & "\class_summary.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Class", "Websites", "Share"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Class", type text}, {"Websites", Int64.Type}, {"Share", type number}}, "en-US")
in
    Typed

// Query: QualitySummary
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/quality_summary.csv"]) else File.Contents(DataFolder & "\quality_summary.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Check", "Count"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Check", type text}, {"Count", Int64.Type}}, "en-US")
in
    Typed

// Query: TldSummary
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/tld_summary.csv"]) else File.Contents(DataFolder & "\tld_summary.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"TLD", "Hosts", "Phishing", "PhishingRate"}),
    Typed = Table.TransformColumnTypes(Selected, {{"TLD", type text}, {"Hosts", Int64.Type}, {"Phishing", Int64.Type}, {"PhishingRate", type number}}, "en-US")
in
    Typed

// Query: LengthDistribution
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/length_distribution.csv"]) else File.Contents(DataFolder & "\length_distribution.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Class", "LengthGroup", "Websites"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Class", type text}, {"LengthGroup", type text}, {"Websites", Int64.Type}}, "en-US")
in
    Typed

// Query: FeatureRates
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/feature_rates.csv"]) else File.Contents(DataFolder & "\feature_rates.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Class", "Feature", "Present", "Hosts", "Rate"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Class", type text}, {"Feature", type text}, {"Present", Int64.Type}, {"Hosts", Int64.Type}, {"Rate", type number}}, "en-US")
in
    Typed

// Query: Rules
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/rule_summary.csv"]) else File.Contents(DataFolder & "\rule_summary.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Rule", "CaughtPhishing", "FlaggedLegitimate", "Recall", "FalsePositiveRate"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Rule", type text}, {"CaughtPhishing", Int64.Type}, {"FlaggedLegitimate", Int64.Type}, {"Recall", type number}, {"FalsePositiveRate", type number}}, "en-US")
in
    Typed

// Query: RuleChart
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/rule_chart.csv"]) else File.Contents(DataFolder & "\rule_chart.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Rule", "Metric", "Rate"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Rule", type text}, {"Metric", type text}, {"Rate", type number}}, "en-US")
in
    Typed

// Query: Evidence
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/statistical_evidence.csv"]) else File.Contents(DataFolder & "\statistical_evidence.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Question", "Feature", "Scope", "Test", "Statistic", "Estimate", "EstimateUnits", "PValueDisplay", "Decision"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Question", Int64.Type}, {"Feature", type text}, {"Scope", type text}, {"Test", type text}, {"Statistic", type number}, {"Estimate", type number}, {"EstimateUnits", type text}, {"PValueDisplay", type text}, {"Decision", type text}}, "en-US")
in
    Typed

// Query: IndicatorDecisions
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/indicator_decisions.csv"]) else File.Contents(DataFolder & "\indicator_decisions.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Feature", "DashboardUse", "ProvenanceNote"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Feature", type text}, {"DashboardUse", type text}, {"ProvenanceNote", type text}}, "en-US")
in
    Typed

// Query: ModelMetricChart
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/model_metric_chart.csv"]) else File.Contents(DataFolder & "\model_metric_chart.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Model", "Metric", "Score"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Model", type text}, {"Metric", type text}, {"Score", type number}}, "en-US")
in
    Typed

// Query: ModelConfusion
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/model_confusion.csv"]) else File.Contents(DataFolder & "\model_confusion.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Actual", "Predicted", "Websites"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Actual", type text}, {"Predicted", type text}, {"Websites", Int64.Type}}, "en-US")
in
    Typed

// Query: ModelPartitions
let
    SourceBinary = if UseBackend then Web.Contents("http://127.0.0.1:8765", [RelativePath="data/model_partitions.csv"]) else File.Contents(DataFolder & "\model_partitions.csv"),
    Source = Csv.Document(SourceBinary, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"Partition", "URLs", "Hosts", "PhishingShare"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Partition", type text}, {"URLs", Int64.Type}, {"Hosts", Int64.Type}, {"PhishingShare", type number}}, "en-US")
in
    Typed
