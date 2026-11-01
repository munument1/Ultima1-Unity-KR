// See https://aka.ms/new-console-template for more information
using Mono.Cecil;
using Mono.Cecil.Cil;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Security.Cryptography;

static IEnumerable<TypeDefinition> Types(IEnumerable<TypeDefinition> roots) {
    foreach (var t in roots) { yield return t; foreach(var n in Types(t.NestedTypes)) yield return n; }
}
static string Operand(Instruction ins, MethodDefinition method) {
    var value=ins.Operand;
    if(ins.OpCode.Code==Code.Ldstr) return "<string>";
    return value switch {
        null => "", Instruction target => "i:"+method.Body.Instructions.IndexOf(target),
        Instruction[] targets => string.Join(",", targets.Select(t=>method.Body.Instructions.IndexOf(t))),
        MemberReference member => member.FullName,
        ParameterDefinition parameter => "p:"+parameter.Index,
        VariableDefinition variable => "v:"+variable.Index,
        _ => Convert.ToString(value,System.Globalization.CultureInfo.InvariantCulture) ?? ""
    };
}
static string[] Shape(MethodDefinition method) => method.Body.Instructions.Select(i=>i.OpCode.Name+"|"+Operand(i,method)).ToArray();
static string[] Exceptions(MethodDefinition method) => method.Body.ExceptionHandlers.Select(e=>e.HandlerType+"|"+e.CatchType?.FullName+"|"+method.Body.Instructions.IndexOf(e.TryStart)+"|"+method.Body.Instructions.IndexOf(e.TryEnd)+"|"+method.Body.Instructions.IndexOf(e.HandlerStart)+"|"+method.Body.Instructions.IndexOf(e.HandlerEnd)+"|"+method.Body.Instructions.IndexOf(e.FilterStart)).ToArray();
if(args.Length is not (3 or 4)) throw new ArgumentException("donor.dll current.dll report.json [detached-candidate.dll]");
if(File.Exists(args[2]) || Path.GetFullPath(args[2])==Path.GetFullPath(args[0]) || Path.GetFullPath(args[2])==Path.GetFullPath(args[1]) || (args.Length==4 && Path.GetFullPath(args[2])==Path.GetFullPath(args[3]))) throw new IOException("Report must be a new file separate from all assemblies");
string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
if(Hash(args[0])!="6c0d01a4b6108a487bd6940df571d10ffc5defc6600b08b76976a26326331b5f" || Hash(args[1])!="7a2125c2fabcf96ab4f6babd17fb76b3cdd688b94c0e88602ef5933c8aa2efe3") throw new InvalidDataException("Unreviewed donor/current assembly hash");
using var donor=AssemblyDefinition.ReadAssembly(args[0]);
using var current=AssemblyDefinition.ReadAssembly(args[1]);
if(current.Name.HasPublicKey) throw new InvalidDataException("Signed assemblies require a separately reviewed signing workflow");
var oldMethods=Types(donor.MainModule.Types).SelectMany(t=>t.Methods).Where(m=>m.HasBody).ToDictionary(m=>m.FullName);
var rows=new List<StringCandidate>();var unmatched=new List<object>();int identical=0,changed=0;
foreach(var m in Types(current.MainModule.Types).SelectMany(t=>t.Methods).Where(m=>m.HasBody)) {
    if(!oldMethods.TryGetValue(m.FullName,out var old)) continue;
    bool equal=Shape(m).SequenceEqual(Shape(old)) && Exceptions(m).SequenceEqual(Exceptions(old)) && m.Body.Variables.Select(v=>v.VariableType.FullName).SequenceEqual(old.Body.Variables.Select(v=>v.VariableType.FullName));
    if(!equal) { changed++; if(old.Body.Instructions.Any(i=>i.OpCode.Code==Code.Ldstr && Regex.IsMatch((string)i.Operand,"[가-힣]"))) unmatched.Add(new {method=m.FullName,oldInstructions=old.Body.Instructions.Count,newInstructions=m.Body.Instructions.Count}); continue; }
    identical++;
    for(int i=0;i<m.Body.Instructions.Count;i++) {
        var ins=m.Body.Instructions[i]; if(ins.OpCode.Code!=Code.Ldstr)continue;
        string source=(string)ins.Operand,translation=(string)old.Body.Instructions[i].Operand;
        if(source!=translation) rows.Add(new StringCandidate(m.FullName,i,source,translation,Regex.IsMatch(translation,"[가-힣]")));
    }
}
var allMethods=Types(current.MainModule.Types).SelectMany(t=>t.Methods).Where(m=>m.HasBody).ToDictionary(m=>m.FullName);
var originalShapes=allMethods.ToDictionary(p=>p.Key,p=>Shape(p.Value));
var originalExceptions=allMethods.ToDictionary(p=>p.Key,p=>Exceptions(p.Value));
var originalLocals=allMethods.ToDictionary(p=>p.Key,p=>p.Value.Body.Variables.Select(v=>v.VariableType.FullName).ToArray());
var patches=new List<StringCandidate>();var rejected=new List<StringCandidate>();
var fontCalls=new List<CallCandidate>();
var fontLoader=allMethods["TMPro.TMP_FontAsset Ultima.Core.UIFonts::FromTtf(System.String)"];
var fontReferences=allMethods.Values.SelectMany(m=>m.Body.Instructions.Select((ins,i)=>new {method=m.FullName,instruction=i,ins})).Where(x=>x.ins.OpCode.Code==Code.Ldstr && ((string)x.ins.Operand).StartsWith("Fonts/")).Select(x=>new {x.method,x.instruction,source=(string)x.ins.Operand,following=allMethods[x.method].Body.Instructions.Skip(x.instruction+1).Take(5).Select(i=>i.OpCode.Name+"|"+Operand(i,allMethods[x.method])).ToArray()}).ToArray();
// Translation memory is an inspection aid only. A matching English word in
// a new method can be a persistence key/resource identifier, not display text.
var sameBodySites=rows.Where(r=>r.hangul).ToDictionary(r=>(r.method,r.instruction));
bool InternalContext(string method) => Regex.IsMatch(method,@"Ultima\.Rendering\.|::(?:Normalize\w*|ClassifyPad|IndexForContinent|AssignShopFromZone|SpawnPurchasedVehicle|GetTransportInventory|GetShopInventory|GetInventory|EnsureSprite|SpawnPlayer|Import)\(") || method.Contains("Ultima.Audio.AudioSetManager::") || (method.Contains("Ultima.Data.") && (method.Contains("::.cctor(") || method.Contains("::.ctor(")));
var quarantined=rows.Where(r=>r.hangul && InternalContext(r.method)).ToArray();
string Tokens(string s) => string.Join("|",Regex.Matches(s,@"\{\d+[^}]*\}|</?(?:color|size|b|i|material)(?:=[^>]+)?>").Select(m=>m.Value));
foreach(var m in allMethods.Values) {
    for(int i=0;i<m.Body.Instructions.Count;i++) {
        var ins=m.Body.Instructions[i];if(ins.OpCode.Code!=Code.Ldstr)continue;
        var source=(string)ins.Operand;
        if(sameBodySites.TryGetValue((m.FullName,i),out var site) && !InternalContext(m.FullName)) {
            var target=site.translation;
            var patch=new StringCandidate(m.FullName,i,source,target,true);
            if(Tokens(source)!=Tokens(target)) {rejected.Add(patch);continue;}
            patches.Add(patch);
        }
        else if(Regex.IsMatch(source,@"^Fonts/(PCSenior|FMTownsUltima|PerfectDOSVGA437|UltimaC64|PrintChar21)( SDF)?$")) {
            if(source!="Fonts/PrintChar21") patches.Add(new StringCandidate(m.FullName,i,source,"Fonts/PrintChar21",false));
            // A baked TMP atlas cannot display the recovered Korean strings.
            // Preserve the one-argument/static/TMP return contract while using
            // the game's existing dynamic TTF loader for these exact sites.
            if(i+1<m.Body.Instructions.Count && m.Body.Instructions[i+1].Operand is GenericInstanceMethod call && call.DeclaringType.FullName=="UnityEngine.Resources" && call.Name=="Load" && call.GenericArguments.Count==1 && call.GenericArguments[0].FullName=="TMPro.TMP_FontAsset") {
                fontCalls.Add(new CallCandidate(m.FullName,i+1,call.FullName,fontLoader.FullName));
            }
        }
    }
}
string? candidateHash=null;
if(args.Length==4) {
    if(File.Exists(args[3]) || Path.GetFullPath(args[3])==Path.GetFullPath(args[1]) || Path.GetFullPath(args[3])==Path.GetFullPath(args[0])) throw new IOException("Candidate must be a new detached file");
    foreach(var p in patches) {var ins=allMethods[p.method].Body.Instructions[p.instruction];if((string)ins.Operand!=p.source)throw new InvalidDataException("Source changed");ins.Operand=p.translation;}
    foreach(var p in fontCalls) {var m=allMethods[p.method];var ins=m.Body.Instructions[p.instruction];if(ins.OpCode.Code!=Code.Call || ((MethodReference)ins.Operand).FullName!=p.source)throw new InvalidDataException("Unreviewed font load call");ins.Operand=fontLoader;originalShapes[p.method][p.instruction]=ins.OpCode.Name+"|"+Operand(ins,m);}
    current.Write(args[3],new WriterParameters {Timestamp=0,DeterministicMvid=true});
    using var check=AssemblyDefinition.ReadAssembly(args[3]);
    var checkedMethods=Types(check.MainModule.Types).SelectMany(t=>t.Methods).Where(m=>m.HasBody).ToDictionary(m=>m.FullName);
    if(!checkedMethods.Keys.ToHashSet().SetEquals(allMethods.Keys))throw new InvalidDataException("Method set changed");
    foreach(var pair in checkedMethods) {
        if(!Shape(pair.Value).SequenceEqual(originalShapes[pair.Key]) || !Exceptions(pair.Value).SequenceEqual(originalExceptions[pair.Key]) || !pair.Value.Body.Variables.Select(v=>v.VariableType.FullName).SequenceEqual(originalLocals[pair.Key])) throw new InvalidDataException("Non-string method semantics changed: "+pair.Key);
        var expected=allMethods[pair.Key].Body.Instructions.Where(i=>i.OpCode.Code==Code.Ldstr).Select(i=>(string)i.Operand);
        if(!pair.Value.Body.Instructions.Where(i=>i.OpCode.Code==Code.Ldstr).Select(i=>(string)i.Operand).SequenceEqual(expected))throw new InvalidDataException("String readback differs");
    }
    candidateHash=Hash(args[3]);
}
File.WriteAllText(args[2],JsonSerializer.Serialize(new {donorSha256=Hash(args[0]),currentSha256=Hash(args[1]),candidateSha256=candidateHash,identicalMethods=identical,changedMethods=changed,candidates=rows,unmatchedMethods=unmatched,patches,rejected,fontReferences,fontCalls,quarantined,gameVerified=false,translationReviewComplete=false},new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine($"Unchanged method bodies: {identical}; candidate strings: {rows.Count}; changed methods needing review: {unmatched.Count}");
Console.WriteLine($"Candidate edits: {patches.Count}; rejected token mismatches: {rejected.Count}; SHA256: {candidateHash}");

record StringCandidate(string method,int instruction,string source,string translation,bool hangul);
record CallCandidate(string method,int instruction,string source,string translation);
