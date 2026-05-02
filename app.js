// IFC File Parser and Element Viewer
class IFCViewer {
    constructor() {
        this.elements = [];
        this.filteredElements = [];
        this.setupEventListeners();
    }

    setupEventListeners() {
        const fileInput = document.getElementById('ifcFile');
        const searchBox = document.getElementById('searchBox');

        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        searchBox.addEventListener('input', (e) => this.filterElements(e.target.value));
    }

    async handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        document.getElementById('fileName').textContent = `Selected: ${file.name}`;
        this.showLoading();

        try {
            const arrayBuffer = await file.arrayBuffer();
            await this.parseIFCFile(arrayBuffer);
        } catch (error) {
            this.showError('Error reading file: ' + error.message);
        }
    }

    async parseIFCFile(arrayBuffer) {
        try {
            // Parse IFC file as text (STEP format)
            const elements = this.parseIFCText(arrayBuffer);
            this.elements = elements;
            this.filteredElements = elements;
            this.displayResults();
        } catch (error) {
            this.showError('Error parsing IFC file: ' + error.message);
        }
    }

    parseIFCText(arrayBuffer) {
        const text = new TextDecoder('utf-8').decode(arrayBuffer);
        const elements = [];
        
        // IFC files can have multi-line entities, so we need to handle that
        // First, let's find all entity definitions
        const entityPattern = /#(\d+)=([A-Z][A-Z0-9_]*)\s*\(/g;
        let match;
        
        // Find all entity matches with their positions
        const entities = [];
        while ((match = entityPattern.exec(text)) !== null) {
            entities.push({
                id: match[1],
                type: match[2],
                startPos: match.index,
                fullMatch: match[0]
            });
        }

        // For each entity, try to extract the full entity definition
        entities.forEach(entity => {
            // Skip header entities and focus on product-related entities
            if (this.isProductEntity(entity.type)) {
                const entityContent = this.extractEntityContent(text, entity.startPos);
                const properties = this.parseEntityProperties(entityContent, entity.type);
                
                elements.push({
                    id: entity.id,
                    type: entity.type,
                    properties: properties
                });
            }
        });

        return elements;
    }

    isProductEntity(type) {
        // List of IFC product-related entity types
        const productTypes = [
            'IFCPRODUCT',
            'IFCELEMENT',
            'IFCBUILDINGELEMENT',
            'IFCWALL',
            'IFCWALLSTANDARDCASE',
            'IFCSLAB',
            'IFCROOF',
            'IFCBEAM',
            'IFCCOLUMN',
            'IFCDOOR',
            'IFCWINDOW',
            'IFCSTAIR',
            'IFCSTAIRFLIGHT',
            'IFCRAMP',
            'IFCFOUNDATION',
            'IFCFOOTING',
            'IFCSPACE',
            'IFCROOM',
            'IFCBUILDING',
            'IFCBUILDINGSTOREY',
            'IFCSITE',
            'IFCPROJECT',
            'IFCCHIMNEY',
            'IFCMEMBER',
            'IFCPLATE',
            'IFCCURTAINWALL',
            'IFCMEMBER',
            'IFCOPENINGELEMENT',
            'IFCSHADINGDEVICE',
            'IFCFURNISHINGELEMENT',
            'IFCDISTRIBUTIONELEMENT',
            'IFCFLOWTERMINAL',
            'IFCFLOWSEGMENT',
            'IFCFLOWCONTROLLER',
            'IFCFLOWMOVINGDEVICE',
            'IFCFLOWSTORAGEDEVICE',
            'IFCFLOWTREATMENTDEVICE',
            'IFCENERGYCONVERSIONDEVICE',
            'IFCELECTRICALELEMENT',
            'IFCLIGHTFIXTURE',
            'IFCELECTRICDISTRIBUTIONBOARD',
            'IFCELECTRICGENERATOR',
            'IFCELECTRICMOTOR',
            'IFCELECTRICTIMECONTROL',
            'IFCFLOWINSTRUMENT',
            'IFCJUNCTIONBOX',
            'IFCLAMP',
            'IFCLIGHTFIXTURE',
            'IFCMEDIA',
            'IFCOUTLET',
            'IFCPROTECTIVEDEVICE',
            'IFCSWITCHINGDEVICE',
            'IFCTRANSFORMER',
            'IFCTUBEBUNDLE',
            'IFCUNITARYCONTROLELEMENT',
            'IFCUNITARYEQUIPMENT',
            'IFCAIRTERMINAL',
            'IFCAIRTERMINALBOX',
            'IFCAIRTOAIRHEATRECOVERY',
            'IFCBOILER',
            'IFCBURNER',
            'IFCCHILLER',
            'IFCCOIL',
            'IFCCOMPRESSOR',
            'IFCCONDENSER',
            'IFCCOOLINGTOWER',
            'IFCCOOLINGTOWER',
            'IFCDAMPER',
            'IFCDUCTFITTING',
            'IFCDUCTSEGMENT',
            'IFCDUCTSILENCER',
            'IFCEVAPORATIVECOOLER',
            'IFCEVAPORATOR',
            'IFCFAN',
            'IFCFILTER',
            'IFCFIRESUPPRESSIONTERMINAL',
            'IFCFLOWMETER',
            'IFCGASTERMINAL',
            'IFCHEATEXCHANGER',
            'IFCHUMIDIFIER',
            'IFCMOTORCONNECTION',
            'IFCOILCOOLER',
            'IFCPIPEFITTING',
            'IFCPIPESEGMENT',
            'IFCPUMP',
            'IFCRADIATOR',
            'IFCREFRIGERATION',
            'IFCSOLARDEVICE',
            'IFCTANK',
            'IFCTERMINAL',
            'IFCTUBEBUNDLE',
            'IFCVALVE',
            'IFCVIBRATIONISOLATOR',
            'IFCWATERHEATER',
            'IFCAIRTERMINAL',
            'IFCDISTRIBUTIONCHAMBERELEMENT',
            'IFCENERGYCONVERSIONDEVICE',
            'IFCFLOWCONTROLLER',
            'IFCFLOWMOVINGDEVICE',
            'IFCFLOWSEGMENT',
            'IFCFLOWSTORAGEDEVICE',
            'IFCFLOWTERMINAL',
            'IFCFLOWTREATMENTDEVICE'
        ];

        return productTypes.some(pt => type.includes(pt) || type === pt);
    }

    extractEntityContent(text, startPos) {
        // Find the opening parenthesis
        let pos = startPos;
        while (pos < text.length && text[pos] !== '(') {
            pos++;
        }
        
        if (pos >= text.length) return '';
        
        // Find matching closing parenthesis
        let depth = 0;
        let content = '';
        for (let i = pos; i < text.length; i++) {
            const char = text[i];
            content += char;
            
            if (char === '(') depth++;
            if (char === ')') {
                depth--;
                if (depth === 0) break;
            }
        }
        
        return content;
    }

    parseEntityProperties(content, type) {
        const props = {};
        
        // Extract name - usually the first or second quoted string
        const nameMatches = content.match(/'([^']*)'/g);
        if (nameMatches && nameMatches.length > 0) {
            // Often the name is in the second or third position
            for (let i = 0; i < Math.min(3, nameMatches.length); i++) {
                const name = nameMatches[i].replace(/'/g, '');
                if (name && name !== '$' && name.length > 0) {
                    props.name = name;
                    break;
                }
            }
        }
        
        // Extract GlobalId - usually a 22-character GUID
        const guidPattern = /['"]([0-9A-Za-z]{22})['"]/;
        const guidMatch = content.match(guidPattern);
        if (guidMatch) {
            props.globalId = guidMatch[1];
        }
        
        // Extract Tag if present
        const tagMatches = content.match(/Tag\s*=\s*'([^']*)'/);
        if (tagMatches) {
            props.tag = tagMatches[1];
        }
        
        return props;
    }

    filterElements(searchTerm) {
        const term = searchTerm.toLowerCase();
        this.filteredElements = this.elements.filter(element => 
            element.type.toLowerCase().includes(term) ||
            (element.properties.name && element.properties.name.toLowerCase().includes(term)) ||
            element.id.toString().includes(term)
        );
        this.displayElements();
    }

    showLoading() {
        const resultsSection = document.getElementById('resultsSection');
        resultsSection.classList.add('active');
        resultsSection.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading and parsing IFC file...</p></div>';
    }

    showError(message) {
        const resultsSection = document.getElementById('resultsSection');
        resultsSection.classList.add('active');
        resultsSection.innerHTML = `<div class="error">${message}</div>`;
    }

    displayResults() {
        const resultsSection = document.getElementById('resultsSection');
        resultsSection.classList.add('active');
        
        // Display statistics
        this.displayStats();
        
        // Display elements
        this.displayElements();
    }

    displayStats() {
        const statsDiv = document.getElementById('stats');
        const typeCount = new Map();
        
        this.elements.forEach(element => {
            const count = typeCount.get(element.type) || 0;
            typeCount.set(element.type, count + 1);
        });

        const statsHTML = `
            <div class="stat-card">
                <h3>${this.elements.length}</h3>
                <p>Total Elements</p>
            </div>
            <div class="stat-card">
                <h3>${typeCount.size}</h3>
                <p>Element Types</p>
            </div>
            <div class="stat-card">
                <h3>${Math.max(...Array.from(typeCount.values()))}</h3>
                <p>Most Common Type Count</p>
            </div>
        `;
        
        statsDiv.innerHTML = statsHTML;
    }

    displayElements() {
        const elementsList = document.getElementById('elementsList');
        
        if (this.filteredElements.length === 0) {
            elementsList.innerHTML = '<div class="element-item"><p>No elements found matching your search.</p></div>';
            return;
        }

        // Group by type
        const grouped = new Map();
        this.filteredElements.forEach(element => {
            if (!grouped.has(element.type)) {
                grouped.set(element.type, []);
            }
            grouped.get(element.type).push(element);
        });

        let html = '';
        grouped.forEach((items, type) => {
            html += `<div class="element-item" style="background: #f0f0f0; font-weight: bold; color: #333;">
                <div class="element-type">${type} (${items.length})</div>
            </div>`;
            
            items.forEach(item => {
                const name = item.properties.name || 'Unnamed';
                const globalId = item.properties.globalId || '';
                html += `
                    <div class="element-item">
                        <div class="element-type">#${item.id}</div>
                        <div class="element-details">
                            ${name !== 'Unnamed' ? `Name: ${name}<br>` : ''}
                            ${globalId ? `GlobalId: ${globalId}<br>` : ''}
                            Type: ${item.type}
                        </div>
                    </div>
                `;
            });
        });

        elementsList.innerHTML = html;
    }
}

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new IFCViewer();
});

